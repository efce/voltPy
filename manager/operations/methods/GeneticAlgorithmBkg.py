import numpy as np
from overrides import overrides
from django.utils import timezone
import manager.operations.method as method
from manager.operations.methodsteps.selectpoint import SelectPoint
from manager.operations.methodsteps.selectrange import SelectRange
from manager.helpers.genetic_algorithm.genetic_algorithm import geneticAlgorithm
from manager.exceptions import VoltPyNotAllowed
from manager.exceptions import VoltPyFailed


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
    description = """
[1] Application of genetic algorithm for baseline optimization in standard addition voltammetry / Łukasz GÓRSKI, Małgorzata JAKUBOWSKA, Bogusław BAŚ, Władysław W. KUBIAK // Journal of Electroanalytical Chemistry ; ISSN 1572-6657. — 2012 vol. 684, s. 38–46. — Bibliogr. s. 46, Abstr.. — tekst: http://www.sciencedirect.com/science/article/pii/S1572665712003177/pdfft?md5=89a1f051feed10aaf624fbdca4d1a1a7&pid=1-s2.0-S1572665712003177-main.pdf
    """

    @classmethod
    def __str__(cls):
        return "Genetic Algorithm for Background Correction"

    def apply(self, user, curveSet):
        if self.model.completed is not True:
            raise VoltPyNotAllowed('Incomplete procedure.')
        self.__perform(curveSet)

    def __perform(self, curveSet):
        cd1 = curveSet.curvesData.all()[0]
        peak_max_index = cd1.xValue2Index(self.model.customData['PeakMaximum'])
        peak_start_index = cd1.xValue2Index(self.model.customData['PeakSpan'][0])
        peak_end_index = cd1.xValue2Index(self.model.customData['PeakSpan'][1])
        if peak_end_index < peak_start_index:
            peak_end_index, peak_start_index = peak_start_index, peak_end_index
        yvecs = np.stack([cd.yVector.T for cd in curveSet.curvesData.all()])
        yvecs = yvecs.T
        print(yvecs.shape)
        (no_bkg, bkg) = geneticAlgorithm(yvecs, peak_max_index, peak_start_index, peak_end_index)
        for i, cd in enumerate(curveSet.curvesData.all()):
            newcd = cd.getCopy()
            newcdConc = curveSet.getCurveConcDict(cd)
            newcd.yVector = no_bkg.T[:, i]
            newcd.date = timezone.now()
            newcd.save()
            curveSet.removeCurve(cd)
            curveSet.addCurve(newcd, newcdConc)
        curveSet.save()

    def finalize(self, user):
        try:
            self.model.customData['PeakMaximum'] = float(self.model.stepsData['SelectPoint'])
            self.model.customData['PeakSpan'] = self.model.stepsData['SelectRange']
        except ValueError:
            raise VoltPyFailed('No values selected.')
        self.__perform(self.model.curveSet)
        self.model.step = None
        self.model.completed = True
        self.model.save()

main_class = GeneticAlgorithmBkg
