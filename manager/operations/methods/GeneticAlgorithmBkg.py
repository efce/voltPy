import numpy as np
from overrides import overrides
from django.utils import timezone
import manager.operations.method as method
from manager.operations.methodsteps.selectpoint import SelectPoint
from manager.operations.methodsteps.selectrange import SelectRange
from manager.helpers.genetic_algorithm.genetic_algorithm import geneticAlgorithm
from manager.exceptions import VoltPyNotAllowed
from manager.exceptions import VoltPyFailed
from manager.operations.checks.check_datalenuniform import check_datalenuniform


class GeneticAlgorithmBkg(method.ProcessingMethod):
    can_be_applied = True
    _steps = [
        {
            'class': SelectPoint,
            'title': 'Select peak maximum.',
            'desc': 'Select maximum of the peaks of interest.',
        },
        {
            'class': SelectRange,
            'title': 'Select peak interval.',
            'desc': 'Select approximate interval of the peak.',
        },
    ]
    model = None
    checks = (check_datalenuniform, )
    description = """
Genetic algorithm is procedure of baseline correction in voltammetry
which utilizes genetic algorithm and spline functions. According to this
method the background shape is modeled by the application of the approach
which operates on natural selection phenomena. The optimization criterion
is constructed with the usage of the three parameters of the voltammogram:
peak’s height, and shape of the peak base [1].<br />
<br />
[1] Ł. Górski, M. Jakubowska, B. Baś, and W. W. Kubiak,
"Application of genetic algorithm for baseline optimization
in standard addition voltammetry" J. Electroanal. Chem., 2012, 684, 38–46.
<br />doi: 10.1016/j.jelechem.2012.08.014
    """

    @classmethod
    def __str__(cls):
        return "Genetic Algorithm for Background Correction"

    def apply(self, user, dataset):
        if self.model.completed is not True:
            raise VoltPyNotAllowed('Incomplete procedure.')
        self.__perform(dataset)

    def __perform(self, dataset):
        cd1 = dataset.curves_data.all()[0]
        peak_max_index = cd1.xValue2Index(self.model.custom_data['PeakMaximum'])
        peak_start_index = cd1.xValue2Index(self.model.custom_data['PeakSpan'][0])
        peak_end_index = cd1.xValue2Index(self.model.custom_data['PeakSpan'][1])
        if peak_end_index < peak_start_index:
            peak_end_index, peak_start_index = peak_start_index, peak_end_index
        yvecs = np.stack([cd.yVector.T for cd in dataset.curves_data.all()])
        yvecs = yvecs.T
        (no_bkg, bkg) = geneticAlgorithm(yvecs, peak_max_index, peak_start_index, peak_end_index)
        for i, cd in enumerate(dataset.curves_data.all()):
            newcd = cd.getCopy()
            newcdConc = dataset.getCurveConcDict(cd)
            newcd.yVector = no_bkg.T[:, i]
            newcd.date = timezone.now()
            newcd.save()
            dataset.removeCurve(cd)
            dataset.addCurve(newcd, newcdConc)
        dataset.save()

    def finalize(self, user):
        try:
            self.model.custom_data['PeakMaximum'] = float(SelectPoint.getData(self))
            self.model.custom_data['PeakSpan'] = SelectRange.getData(self)
        except ValueError:
            raise VoltPyFailed('No values selected.')
        self.__perform(self.model.dataset)
        self.model.step = None
        self.model.completed = True
        self.model.save()

main_class = GeneticAlgorithmBkg
