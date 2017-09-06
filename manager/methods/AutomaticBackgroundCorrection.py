from copy import deepcopy
from django.utils import timezone
from manager.methodmanager import *
from manager.helpers.bkghelpers import calc_abc

class AutomaticBackgroundCorrection(ProcessingMethod):
    steps = [ 
                {
                    'step': MethodManager.Step.end,
                    'title': 'End',
                    'data': ''
                }
            ]
    model = None


    def __init__(self):
        pass


    def __str__(self):
        return "Automatic Background Correction"


    def getStep(self, stepNum):
        if ( stepNum >= len(self.steps) ):
            return None
        return self.steps[stepNum]


    def processStep(self, user, stepNum, data):
        return True
        


    def finalize(self, *args, **kwargs):
        import numpy as np
        if self.model.curveSet.locked:
            raise ValueError("CurveSet used by Analysis method cannot be changed.")
        for cd in self.model.curveSet.usedCurveData.all():
            newcd = deepcopy(cd)
            newcd.id = None
            newcd.pk = None
            xvec = range(len(cd.current))
            yvec = cd.current
            self.model.customData['iter'] = 20
            self.model.customData['degree'] = 5
            yvec = calc_abc(xvec, yvec, 5, 20)['yvec']
            newcd.current = yvec
            newcd.method=self.__repr__()
            newcd.date=timezone.now()
            newcd.processing=self.model
            newcd.save()
            self.model.curveSet.usedCurveData.remove(cd)
            self.model.curveSet.usedCurveData.add(newcd)
            self.model.curveSet.save()
            self.model.save()
        return True


    def printInfo(self, user):
        return {
                'head': '',
                'body': ''
            }

def newInstance(*args, **kwargs):
    return AutomaticBackgroundCorrection(*args, **kwargs)
