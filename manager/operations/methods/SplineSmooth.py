import numpy as np
from overrides import overrides
from scipy.interpolate import UnivariateSpline
import manager.operations.method as method
from manager.operations.methodsteps.settings import Settings
from manager.helpers.validators import validate_0_to_1
from manager.exceptions import VoltPyNotAllowed


class SplineSmooth(method.ProcessingMethod):
    can_be_applied = True
    _steps = [
        {
            'class': Settings,
            'title': 'Confirm settings.',
            'desc': 'Set Spline Smoothing settings.',
        },
    ]
    description = """
Smoothing Spline algorithm fits into the signal spline with number of knots
governed by the smoothing factor, the lower the factor the more knots are used.
With factor = 0, there is no smoothing as number of knots is equal to the number
of points in the signal. With factor = 1 the whole signal is represented as a
2nd degree polynomial.
    """

    @classmethod
    def __str__(cls):
        return "Smoothing Spline"

    @overrides
    def initialForStep(self, step_num: int):
        if step_num == 0:
            return {
                'Smoothing factor': {
                    'default': 0.01,
                    'validator': validate_0_to_1,
                }
            }
        return None

    def apply(self, user, dataset):
        if self.model.completed is not True:
            raise VoltPyNotAllowed('Incomplete procedure.')
        self.__perform(dataset)

    def __perform(self, dataset):
        factor = self.model.custom_data['Factor']
        for cd in dataset.curves_data.all():
            newcd = cd.getCopy()
            newcdConc = dataset.getCurveConcDict(cd)
            yvec = newcd.yVector
            xvec = newcd.xVector
            spline_fit = UnivariateSpline(xvec, yvec)
            spline_fit.set_smoothing_factor(factor)
            newyvec = spline_fit(xvec)
            newcd.yVector = newyvec
            newcd.save()
            dataset.removeCurve(cd)
            dataset.addCurve(newcd, newcdConc)
        dataset.save()

    def finalize(self, user):
        self.model.custom_data['Factor'] = self.model.steps_data['Settings']['Smoothing factor']
        self.__perform(self.model.dataset)
        self.model.step = None
        self.model.completed = True
        self.model.save()
        return True

main_class = SplineSmooth
