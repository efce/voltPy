from copy import deepcopy
from django.utils import timezone
from manager.methodmanager import *
import numpy as np

class PolynomialBackgroundFit(ProcessingMethod):
    steps = [ 
                {
                    'step': MethodManager.Step.selectTwoRanges,
                    'title': 'Choose two fit intervals.',
                    'data': { 
                        'starting': ((0,0),(0,0)),
                        'desc': 'Select two fit intervals.',
                    }
                },
                {
                    'step': MethodManager.Step.confirmation,
                    'title': 'Choose two fit intervals.',
                    'data': { 
                        'starting': '',
                        'desc': 'Confirm background shape.',
                    }
                },
                {
                    'step': MethodManager.Step.end,
                    'title': 'End',
                    'data': ''
                }
            ]
    model = None
    degree = 3


    def __init__(self):
        pass


    def __str__(self):
        return "3rd deg Polynomial Background Fit"


    def getStep(self, stepNum):
        if ( stepNum >= len(self.steps) ):
            return None
        return self.steps[stepNum]

    def processStep(self, user, stepNum):
        if ( stepNum == 0 ):
            print( 'processing step for num: %i' %stepNum)
            self.model.customData['fitCoeff'] = []
            for cd in self.model.curveSet.usedCurveData.all():
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
            self.model.step = self.model.step+1
            self.model.save()
        elif ( stepNum == 1 ):
            self.model.step = self.model.step+1
            self.model.save()
        return True

    def getAddToPlot(self, currentStepNumber):
        print( 'addtoplot for num: %i' %currentStepNumber)
        if ( currentStepNumber == 1 ):
            fitlines = []
            for cd,fit in zip(self.model.curveSet.usedCurveData.all(), self.model.customData['fitCoeff']):
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

    def finalize(self, *args, **kwargs):
        print('finalizing')
        import numpy as np
        if self.model.curveSet.locked:
            raise ValueError("CurveSet used by Analysis method cannot be changed.")
        for cd,fit in zip(self.model.curveSet.usedCurveData.all(), self.model.customData['fitCoeff']):
            newcd = deepcopy(cd)
            newcd.id = None
            newcd.pk = None
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
            newcd.save()
            self.model.curveSet.usedCurveData.remove(cd)
            self.model.curveSet.usedCurveData.add(newcd)
            self.model.curveSet.save()
            self.model.step = self.model.step+1
            self.model.completed = True
            self.model.save()
        return True


    def printInfo(self, request, user):
        return {
                'head': '',
                'body': ''
            }

def newInstance(*args, **kwargs):
    return PolynomialBackgroundFit(*args, **kwargs)
