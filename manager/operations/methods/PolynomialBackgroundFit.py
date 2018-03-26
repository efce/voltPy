import numpy as np
import manager.operations.method as method
from manager.operations.methodsteps.selecttworanges import SelectTwoRanges
from manager.operations.methodsteps.confirmation import Confirmation


class PolynomialBackgroundFit(method.ProcessingMethod):
    _steps = [ 
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
    degree = 3
    description = """
The polynomial fit is the most wiedly used background correction method,
where the polynomial of given order (in this case 3rd) is fitted into two
intevals -- one should be directly in front of the peak of interest and
other right after it.
    """

    @classmethod
    def __str__(cls):
        return "3rd deg Polynomial Background Fit"

    def process(self, user, request):
        ret = super(PolynomialBackgroundFit, self).process(user, request)
        self.model.customData['fitCoeff'] = []
        if self.model.active_step_num == 1:
            for cd in self.model.curveSet.curvesData.all():
                st1 = cd.xvalueToIndex(user, self.model.stepsData['SelectTwoRanges'][0])
                en1 = cd.xvalueToIndex(user, self.model.stepsData['SelectTwoRanges'][1])
                st2 = cd.xvalueToIndex(user, self.model.stepsData['SelectTwoRanges'][2])
                en2 = cd.xvalueToIndex(user, self.model.stepsData['SelectTwoRanges'][3])
                xvec = cd.xVector[st1:en1]
                xvec.extend(cd.xVector[st2:en2])
                yvec = cd.yVector[st1:en1]
                yvec.extend(cd.yVector[st2:en2])
                p = np.polyfit(xvec, yvec, self.degree)
                self.model.customData['fitCoeff'].append({'x3': p[0], 'x2': p[1], 'x1': p[2], 'x0': p[3]})
                self.model.save()
        return ret

    def getAddToPlot(self):
        if self.model.active_step_num == 1:
            fitlines = []
            for cd, fit in zip(self.model.curveSet.curvesData.all(), self.model.customData['fitCoeff']):
                xvec = cd.xVector
                p = (fit['x3'], fit['x2'], fit['x1'], fit['x0'])
                fitlines.append(dict(
                    x=xvec,
                    y=np.polyval(p, xvec).tolist(),
                    plottype='line',
                    color='red',
                ))
            return fitlines
        else:
            return None

    def finalize(self, user):
        import numpy as np
        cs = self.model.curveSet
        if cs.locked:
            raise ValueError("CurveSet used by Analysis method cannot be changed.")
        for cd, fit in zip(cs.curvesData.all(), self.model.customData['fitCoeff']):
            newcd = cd.getCopy()
            newcdConc = cs.getCurveConcDict(cd)
            yvec = newcd.yVector
            xvec = newcd.xVector
            p = (fit['x3'], fit['x2'], fit['x1'], fit['x0'])
            ybkg = np.polyval(p, xvec)
            newyvec = list(np.subtract(yvec, ybkg))
            newcd.yVector = newyvec
            newcd.save()
            cs.removeCurve(cd)
            cs.addCurve(newcd, newcdConc)
        cs.save()
        self.model.save()
        return True

    def getInfo(self, request, user):
        return {
            'head': '',
            'body': ''
        }

main_class = PolynomialBackgroundFit
