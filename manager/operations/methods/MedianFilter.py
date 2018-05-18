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
            'title': 'Apply median filter',
            'desc': 'Press forward to apply Median Filter.',
        },
    ]
    degree = 3
    description = """
    Median filter.
    """

    @classmethod
    def __str__(cls):
        return "Median Filter"

    def apply(self, user, dataset):
        if self.model.completed is not True:
            raise VoltPyNotAllowed('Incomplete procedure.')
        self.__perform(dataset)

    def __perform(self, dataset):
        for cd in dataset.curves_data.all():
            newcd = cd.getCopy()
            newcdConc = dataset.getCurveConcDict(cd)
            yvec = newcd.yVector
            xvec = newcd.xVector
            newyvec = medfilt(yvec)
            newcd.yVector = newyvec
            newcd.save()
            dataset.removeCurve(cd)
            dataset.addCurve(newcd, newcdConc)
        dataset.save()

    def finalize(self, user):
        self.__perform(self.model.dataset)
        self.model.step = None
        self.model.completed = True
        self.model.save()
        return True

main_class = MedianFilter
