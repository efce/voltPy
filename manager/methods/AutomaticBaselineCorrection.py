from copy import deepcopy
from django.utils import timezone
import numpy as np
import manager.methodmanager as mm
from manager.helpers.bkghelpers import calc_abc

class AutomaticBaselineCorrection(mm.ProcessingMethod):
    _operations = [ 
        {
            'class': mm.OperationConfirmation,
            'title': 'Config before proceding.',
            'desc': 'Confirm before proceding.',
        },
    ]
    model = None
    description = """
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
            newcd.basedOn = cd
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

main_class = AutomaticBaselineCorrection
