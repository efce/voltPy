import numpy as np
from overrides import overrides
import manager.operations.method as method
from manager.operations.methodsteps.selecttworanges import SelectTwoRanges
from manager.operations.methodsteps.confirmation import Confirmation
from manager.operations.methodsteps.settings import Settings
from manager.exceptions import VoltPyNotAllowed
from manager.exceptions import VoltPyFailed


class PolynomialBackgroundFit(method.ProcessingMethod):
    can_be_applied = True
    _steps = [
        {
            'class': Settings,
            'title': 'Method settings.',
            'desc': 'Change methods settings.',
        },
        {
            'class': SelectTwoRanges,
            'title': 'Choose two fit intervals.',
            'desc': 'Select two fit intervals and press Forward, or press Back to change the selection.',
        },
        {
            'class': Confirmation,
            'title': 'Confirm background shape.',
            'desc': 'Press Forward to confirm background shape or press Back to return to interval selection.',
        },
    ]
    description = """
The polynomial fit is the most wiedly used background correction method,
where the polynomial of given order (in this case 3rd) is fitted into two
intevals -- one should be directly in front of the peak of interest and
other right after it.
    """

    @classmethod
    def __str__(cls):
        return "Polynomial Background Fit"

    def process(self, user, request):
        ret = super(PolynomialBackgroundFit, self).process(user, request)
        self.model.customData['fitCoeff'] = []
        if self.model.active_step_num == 2:
            for cd in self.model.curveSet.curvesData.all():
                v = []
                v.append(cd.xValue2Index(self.model.stepsData['SelectTwoRanges'][0]))
                v.append(cd.xValue2Index(self.model.stepsData['SelectTwoRanges'][1]))
                v.append(cd.xValue2Index(self.model.stepsData['SelectTwoRanges'][2]))
                v.append(cd.xValue2Index(self.model.stepsData['SelectTwoRanges'][3]))
                v.sort()
                (st1, en1, st2, en2) = (v[0], v[1], v[2], v[3])
                xvec = cd.xVector[st1:en1]
                xvec.extend(cd.xVector[st2:en2])
                yvec = cd.yVector[st1:en1]
                yvec.extend(cd.yVector[st2:en2])
                try:
                    degree = int(self.model.stepsData['Settings']['Degree'])
                except ValueError:
                    raise VoltPyFailed('Wrong degree of polynomial')
                p = np.polyfit(xvec, yvec, degree)
                self.model.customData['fitCoeff'].append(p)
                self.model.save()
        return ret

    @overrides
    def initialForStep(self, step_num):
        from manager.helpers.validators import validate_polynomial_degree

        if step_num == 0:
            return {
                'Degree': {
                    'default': 3,
                    'validator': validate_polynomial_degree
                }
            }
        return None

    @overrides
    def addToMainPlot(self):
        if self.model.active_step_num == 2:
            fitlines = []
            for cd, fit in zip(self.model.curveSet.curvesData.all(), self.model.customData['fitCoeff']):
                xvec = cd.xVector
                p = fit
                fitlines.append(dict(
                    x=xvec,
                    y=np.polyval(p, xvec).tolist(),
                    plottype='line',
                    color='red',
                ))
            return fitlines
        else:
            return None

    def apply(self, user, curveSet):
        if self.model.completed is not True:
            raise VoltPyNotAllowed('Incomplete procedure.')
        self.__perform(curveSet)

    def __perform(self, curveSet):
        for cd, fit in zip(curveSet.curvesData.all(), self.model.customData['fitCoeff']):
            newcd = cd.getCopy()
            newcdConc = curveSet.getCurveConcDict(cd)
            yvec = newcd.yVector
            xvec = newcd.xVector
            p = fit
            ybkg = np.polyval(p, xvec)
            newyvec = list(np.subtract(yvec, ybkg))
            newcd.yVector = newyvec
            newcd.save()
            curveSet.removeCurve(cd)
            curveSet.addCurve(newcd, newcdConc)
        curveSet.save()

    def finalize(self, user):
        self.__perform(self.model.curveSet)
        self.model.step = None
        self.model.completed = True
        self.model.save()
        return True

main_class = PolynomialBackgroundFit
