from django.utils import timezone
import manager.operations.method as method
from manager.operations.methodsteps.confirmation import Confirmation
from manager.helpers.bkghelpers import calc_abc
from manager.exceptions import VoltPyNotAllowed


class AutomaticBaselineCorrection(method.ProcessingMethod):
    can_be_applied = True
    _steps = [
        {
            'class': Confirmation,
            'title': 'Config before proceding.',
            'desc': 'To confirm press Forward.',
        },
    ]
    model = None
    description = """
Automatic Baseline Correction (ABC) removes the background by the means
of automatic polynomial fitting. This implementation is taken from [1].
ABC usually two parameters to work, however, there are some values
which offer better performance, therefore, here the number of iterations
and polynomial degree are set to 40 and 4 respectivly.

[1] Górski, Ł., Ciepiela, F., & Jakubowska, M. (2014). Automatic
baseline correction in voltammetry. Electrochimica Acta, 136, 195–203.
https://doi.org/10.1016/j.electacta.2014.05.076
    """

    @classmethod
    def __str__(cls):
        return "Automatic Baseline Correction"

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
        self.model.customData['iterations'] = 50
        self.model.customData['degree'] = 4
        self.__perform(self.model.curveSet)
        self.model.step = None
        self.model.completed = True
        self.model.save()

main_class = AutomaticBaselineCorrection
