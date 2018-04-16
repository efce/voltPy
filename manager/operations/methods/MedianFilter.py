import numpy as np
from overrides import overrides
from scipy.signal import medfilt
import manager.operations.method as method
from manager.operations.methodsteps.confirmation import Confirmation
from manager.exceptions import VoltPyNotAllowed


class MedianFilter(method.ProcessingMethod):
    can_be_applied = True
    _steps = [
        {
            'class': Confirmation,
            'title': 'Confirm background shape.',
            'desc': 'Press Forward to confirm background shape or press Back to return to interval selection.',
        },
    ]
    degree = 3
    description = """
    Median filter.
    """

    @classmethod
    def __str__(cls):
        return "Median Filter"

    def apply(self, user, curveSet):
        if self.model.completed is not True:
            raise VoltPyNotAllowed('Incomplete procedure.')
        self.__perform(curveSet)

    def __perform(self, curveSet):
        for cd in curveSet.curvesData.all():
            newcd = cd.getCopy()
            newcdConc = curveSet.getCurveConcDict(cd)
            yvec = newcd.yVector
            xvec = newcd.xVector
            newyvec = medfilt(yvec)
            newcd.yVector = newyvec
            newcd.save()
            curveSet.removeCurve(cd)
            curveSet.addCurve(newcd, newcdConc)
        curveSet.save()

    def finalize(self, user):
        self.__perform(self.model.curveSet)
        self.model.step = None
        self.model.completed = True
        self.model.save()
        return True

main_class = MedianFilter
