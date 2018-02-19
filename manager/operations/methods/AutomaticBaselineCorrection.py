from copy import deepcopy
import numpy as np
from django.utils import timezone
import manager.operations.methodmanager as mm
from manager.operations.methodsteps.confirmation import Confirmation
from manager.helpers.bkghelpers import calc_abc

class AutomaticBaselineCorrection(mm.ProcessingMethod):
    _steps = [ 
        {
            'class': Confirmation,
            'title': 'Config before proceding.',
            'desc': 'To confirm press Forward.',
        },
    ]
    model = None
    description = \
"""
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

    def finalize(self, user):
        for cd in self.model.curveSet.curvesData.all():
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
            newcd.basedOn = cd
            newcd.save()
            self.model.curveSet.curvesData.remove(cd)
            self.model.curveSet.curvesData.add(newcd)
            for a in self.model.curveSet.analytes.all():
                self.model.curveSet.analytesConc[a.id][newcd.id] = \
                    self.model.curveSet.analytesConc[a.id].pop(cd.id, 0)
        self.model.curveSet.save()
        self.model.step = None
        self.model.completed = True
        self.model.save()

    def getInfo(self, request, user):
        return {
            'head': '',
            'body': ''
        }

main_class = AutomaticBaselineCorrection
