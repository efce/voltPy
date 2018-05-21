from overrides import overrides
from django.utils import timezone
import manager.operations.method as method
from manager.operations.methodsteps.settings import Settings
from manager.helpers.bkghelpers import calc_abc
from manager.exceptions import VoltPyNotAllowed
from manager.exceptions import VoltPyFailed


class AutomaticBaselineCorrection(method.ProcessingMethod):
    can_be_applied = True
    _steps = [
        {
            'class': Settings,
            'title': 'Method settings.',
            'desc': 'Set method parameters.',
        },
    ]
    model = None
    # TODO: improve description
    description = """
Automatic Baseline Correction (ABC) removes the background by the means
of automatic polynomial fitting. This implementation is taken from [1].
ABC usually two parameters to work, however, there are some values
which offer better performance, therefore, here the number of iterations
and polynomial degree are set to 40 and 4 respectively.<br />
<br />
[1] Ł. Górski, F. Ciepiela, and M. Jakubowska, "Automatic
baseline correction in voltammetry" Electrochimica Acta, 2014, 136, 195–203.
<br />doi: 10.1016/j.electacta.2014.05.076
    """

    @overrides
    def initialForStep(self, step_num):
        from manager.helpers.validators import validate_polynomial_degree
        if step_num == 0:
            return {
                'Degree': {
                    'default': 4,
                    'validator': validate_polynomial_degree
                },
                'Iterations': {
                    'default': 50,
                    'validator': validate_polynomial_degree
                    #  There are the same requirements for iterators as polynomial degree
                }
            }

    @classmethod
    def __str__(cls):
        return "Automatic Baseline Correction"

    def apply(self, user, dataset):
        if self.model.completed is not True:
            raise VoltPyNotAllowed('Incomplete procedure.')
        self.__perform(dataset)

    def __perform(self, dataset):
        iterations = self.model.custom_data['iterations']
        degree = self.model.custom_data['degree']
        for cd in dataset.curves_data.all():
            newcd = cd.getCopy()
            newcdConc = dataset.getCurveConcDict(cd)
            yvec = newcd.yVector
            xvec = range(len(yvec))
            yvec = calc_abc(xvec, yvec, degree, iterations)['yvec']
            newcd.yVector = yvec
            newcd.date = timezone.now()
            newcd.save()
            dataset.removeCurve(cd)
            dataset.addCurve(newcd, newcdConc)
        dataset.save()

    def finalize(self, user):
        try:
            self.model.custom_data['iterations'] = int(self.model.steps_data['Settings']['Iterations'])
            self.model.custom_data['degree'] = int(self.model.steps_data['Settings']['Degree'])
        except ValueError:
            raise VoltPyFailed('Wrong values for degree or iterations.')
        self.__perform(self.model.dataset)
        self.model.step = None
        self.model.completed = True
        self.model.save()

main_class = AutomaticBaselineCorrection
