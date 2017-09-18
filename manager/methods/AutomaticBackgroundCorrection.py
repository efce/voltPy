from copy import deepcopy
from django.utils import timezone
import numpy as np
import manager.methodmanager as mm
from manager.helpers.bkghelpers import calc_abc

class AutomaticBackgroundCorrection(mm.ProcessingMethod):
    _operations = [ 
        {
            'class': None,
            'title': 'End',
            'desc': ''
        }
    ]
    model = None

    def __init__(self, model):
        self.model = model

    def __str__(self):
        return "Automatic Background Correction"

    def finalize(self, *args, **kwargs):
        if self.model.curveSet.locked:
            raise ValueError("CurveSet used by Analysis method cannot be changed.")
        for cd in self.model.curveSet.usedCurveData.all():
            newcd = deepcopy(cd)
            newcd.id = None
            newcd.pk = None
            xvec = range(len(cd.current))
            yvec = cd.xVector
            degree = 4
            iterations = 40
            self.model.customData['iterations'] = iterations
            self.model.customData['degree'] = degree
            yvec = calc_abc(xvec, yvec, degree, iterations)['yvec']
            newcd.yVector = yvec
            newcd.method = self.__repr__()
            newcd.date = timezone.now()
            newcd.processing = self.model
            newcd.save()
            self.model.curveSet.usedCurveData.remove(cd)
            self.model.curveSet.usedCurveData.add(newcd)
            self.model.curveSet.save()
            self.model.step = None
            self.model.completed = True
            self.model.save()

    def getInfo(self, request, user):
        return {
            'head': '',
            'body': ''
        }

main_class = AutomaticBackgroundCorrection
