import numpy as np
from django.utils import timezone
import manager.operations.method as method
from manager.operations.methodsteps.confirmation import Confirmation
from manager.helpers.bkghelpers import calc_abc

class AutomaticBaselineCorrection(method.ProcessingMethod):
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
        cs = self.model.curveSet
        for cd in cs.curvesData.all():
            newcd = cd.getCopy()
            newcdConc = cs.getCurveConcDict(cd)
            yvec = newcd.yVector
            xvec = range(len(yvec))
            degree = 4
            iterations = 50
            self.model.customData['iterations'] = iterations
            self.model.customData['degree'] = degree
            yvec = calc_abc(xvec, yvec, degree, iterations)['yvec']
            newcd.yVector = yvec
            newcd.date = timezone.now()
            newcd.save()
            cs.removeCurve(cd)
            cs.addCurve(newcd, newcdConc)
        cs.save()
        self.model.step = None
        self.model.completed = True
        self.model.save()

    def getInfo(self, request, user):
        return {
            'head': '',
            'body': ''
        }

main_class = AutomaticBaselineCorrection
