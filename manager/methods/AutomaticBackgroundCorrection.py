from manager.method_manager import *
from manager.helpers.bkghelpers import calc_abc
from copy import deepcopy
from django.utils import timezone

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
        pass


    def finalize(self, *args, **kwargs):
        import numpy as np
        for cd in self.model.curveSet.usedCurveData.all():
            newcd = deepcopy(cd)
            newcd.id = None
            newcd.pk = None
            xvec = range(len(cd.current))
            yvec = cd.current
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


    def printInfo(self):
        return {
                'head': '',
                'body': ''
            }

def newInstance(*args, **kwargs):
    return AutomaticBackgroundCorrection(*args, **kwargs)
