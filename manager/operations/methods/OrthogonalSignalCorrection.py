from overrides import overrides
from django.utils import timezone
import manager.operations.method as method
from manager.operations.methodsteps.settings import Settings
from manager.helpers.bkghelpers import calc_abc
from manager.exceptions import VoltPyNotAllowed
from manager.exceptions import VoltPyFailed


class OrthogonalSignalCorrection(method.ProcessingMethod):
    can_be_applied = True
    _steps = [
        {
            'class': Settings,
            'title': 'Method settings.',
            'desc': 'Set method parameters.',
        },
    ]
    model = None
    description = """
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
        return "Orthogonal Signal Correction"

    def apply(self, user, curveSet):
        if self.model.completed is not True:
            raise VoltPyNotAllowed('Incomplete procedure.')
        self.__perform(curveSet)

    def __perform(self, curveSet):
        iterations = self.model.customData['iterations']
        degree = self.model.customData['degree']
        for cd in curveSet.curvesData.all():
            newcd = cd.getCopy()
            newcdConc = curveSet.getCurveConcDict(cd)
            yvec = newcd.yVector
            xvec = range(len(yvec))
            yvec = calc_abc(xvec, yvec, degree, iterations)['yvec']
            newcd.yVector = yvec
            newcd.date = timezone.now()
            newcd.save()
            curveSet.removeCurve(cd)
            curveSet.addCurve(newcd, newcdConc)
        curveSet.save()

    def finalize(self, user):
        try:
            self.model.customData['iterations'] = int(self.model.stepsData['Settings']['Iterations'])
            self.model.customData['degree'] = int(self.model.stepsData['Settings']['Degree'])
        except ValueError:
            raise VoltPyFailed('Wrong values for degree or iterations.')
        self.__perform(self.model.curveSet)
        self.model.step = None
        self.model.completed = True
        self.model.save()

main_class = AutomaticBaselineCorrection
