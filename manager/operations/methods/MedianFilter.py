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
            'desc': 'Press Forward to apply Median Filter.',
        },
    ]
    description = """
    Median filter is smoothing algorithm similar to the Savitzky-Golay, however instead of fitting of the polynomial,
    the middle point of the window is moved to the value of median of the points in the window. The median filter is
    most usefull for removal of spikes from the signal (single point large amplitude errors).
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
            yvec = cd.yVector
            xvec = cd.xVector
            newyvec = medfilt(yvec)
            dataset.updateCurve(self.model, cd, newyvec)
        dataset.save()

    def finalize(self, user):
        self.__perform(self.model.dataset)
        self.model.step = None
        self.model.completed = True
        self.model.save()
        return True

main_class = MedianFilter
