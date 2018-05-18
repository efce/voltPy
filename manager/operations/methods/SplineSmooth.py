import numpy as np
from overrides import overrides
from scipy.interpolate import UnivariateSpline
import manager.operations.method as method
from manager.operations.methodsteps.confirmation import Confirmation
from manager.exceptions import VoltPyNotAllowed


class SplineSmooth(method.ProcessingMethod):
    can_be_applied = True
    _steps = [
        {
            'class': Confirmation,
            'title': 'Confirm settings.',
            'desc': 'Confirm the Spline Smoothing.',
        },
    ]
    degree = 3
    description = """
Spline smoothing algorithm.
    """

    @classmethod
    def __str__(cls):
        return "Spline Smooth"

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
            spline_fit = UnivariateSpline(xvec, yvec)
            spline_fit.set_smoothing_factor(0.001)
            newyvec = spline_fit(xvec)
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

main_class = SplineSmooth
