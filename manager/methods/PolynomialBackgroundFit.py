from copy import deepcopy
from django.utils import timezone
import manager.methodmanager as mm
import numpy as np

class PolynomialBackgroundFit(mm.ProcessingMethod):
    _operations = [ 
        {
            'class': mm.OperationSelectTwoRanges,
            'title': 'Choose two fit intervals.',
            'desc': 'Select two fit intervals and press Forward, or press Back to change the selection.',
        },
        {
            'class': mm.OperationConfirmation,
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
        ret = super(mm.ProcessingMethod, self).process(user, request)
        if ( self.model.step == 1 ):
            self.model.customData['fitCoeff'] = []
            for cd in self.model.curveSet.curvesData.all():
                st1 = cd.xvalueToIndex(user, self.model.customData['range1'][0])
                en1 = cd.xvalueToIndex(user, self.model.customData['range1'][1])
                st2 = cd.xvalueToIndex(user, self.model.customData['range2'][0])
                en2 = cd.xvalueToIndex(user, self.model.customData['range2'][1])
                xvec = cd.xVector[st1:en1]
                xvec.extend(cd.xVector[st2:en2])
                yvec = cd.yVector[st1:en1]
                yvec.extend(cd.yVector[st2:en2])
                p = np.polyfit(xvec, yvec, self.degree)
                self.model.customData['fitCoeff'].append({'x3': p[0], 'x2': p[1], 'x1': p[2], 'x0': p[3]})
                self.model.save()
        return ret

    def getAddToPlot(self):
        currentStepNumber = self.model.step
        if ( currentStepNumber == 1 ):
            fitlines = []
            for cd,fit in zip(self.model.curveSet.curvesData.all(), self.model.customData['fitCoeff']):
                xvec = cd.xVector
                polyval = lambda x: (
                    fit['x3']*x**3
                    + fit['x2']*x**2
                    + fit['x1']*x
                    + fit['x0'] )
                fitlines.append(dict(
                    x=xvec,
                    y=[ polyval(a) for a in xvec ],
                    plottype='line',
                    color='red',
                ))
            return fitlines
        else:
            return None

    def finalize(self, user):
        import numpy as np
        if self.model.curveSet.locked:
            raise ValueError("CurveSet used by Analysis method cannot be changed.")
        for cd,fit in zip(self.model.curveSet.curvesData.all(), self.model.customData['fitCoeff']):
            newcd = deepcopy(cd)
            newcd.id = None
            newcd.pk = None
            newcd.date = None
            yvec = cd.yVector
            xvec = cd.xVector
            polyval = lambda x: (
                fit['x3']*x**3
                + fit['x2']*x**2
                + fit['x1']*x
                + fit['x0'] )
            ybkg = [ polyval(a) for a in xvec ]
            newyvec = list(np.subtract(yvec, ybkg));
            newcd.yVector = newyvec
            newcd.method=self.__repr__()
            newcd.date=timezone.now()
            newcd.processing=self.model
            newcd.basedOn = cd
            newcd.save()
            for a in self.model.curveSet.analytes.all():
                self.model.curveSet.analytesConc[a.id][newcd.id] = \
                    self.model.curveSet.analytesConc[a.id].pop(cd.id, 0)
            self.model.curveSet.curvesData.remove(cd)
            self.model.curveSet.curvesData.add(newcd)
            self.model.curveSet.save()
            self.model.save()
        return True


    def getInfo(self, request, user):
        return {
            'head': '',
            'body': ''
        }

main_class = PolynomialBackgroundFit
