from copy import deepcopy
from django.utils import timezone
import numpy as np
import manager.methodmanager as mm
from manager.helpers.bkghelpers import calc_abc

class AutomaticBackgroundCorrection(mm.ProcessingMethod):
    _operations = [ 
        {
            'class': mm.OperationConfirmation,
            'title': 'Config before proceding.',
            'desc': 'Confirm before proceding.',
        },
    ]
    model = None

    def __str__(self):
        return "Automatic Background Correction"

    def finalize(self, user):
        for cd in self.model.curveSet.usedCurveData.all():
            newcd = deepcopy(cd)
            newcd.id = None
            newcd.pk = None
            newcd.date = None
            xvec = range(len(cd.current))
            yvec = cd.yVector
            degree = 4
            iterations = 50
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
