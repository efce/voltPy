import numpy as np
from overrides import overrides
from scipy.signal import savgol_filter
import manager.operations.method as method
from manager.operations.methodsteps.selecttworanges import SelectTwoRanges
from manager.operations.methodsteps.settings import Settings
from manager.exceptions import VoltPyNotAllowed
from manager.exceptions import VoltPyFailed


class SGSmooth(method.ProcessingMethod):
    can_be_applied = True
    _steps = [
        {
            'class': Settings,
            'title': 'Confirm settings.',
            'desc': 'Confirm the settings of Savitzky-Golay smoothing.',
        },
    ]
    degree = 3
    description = """
Savitzky-Golay smoothing (filtering) is an iterative algorithm where polynomial
of a given order is fitted into an odd size window, and the middle point
of the window is moved to the place given by the polynomial. When the point is
replaced, the window moves one point right and the procedure is repeated
until the last point is reached. Both the polynomial degree and the window size
 may be defined.
    """

    @classmethod
    def __str__(cls):
        return "Savitzky-Golay Smoothing"

    @overrides
    def initialForStep(self, step_num):
        from manager.helpers.validators import validate_polynomial_degree
        from manager.helpers.validators import validate_window_span
        
        if step_num == 0:
            return {
                'Window Span': {
                    'default': 13, 
                    'validator': validate_window_span
                }, 
                'Degree': {
                    'default': 3,
                    'validator': validate_polynomial_degree
                }
            }
        return None

    def apply(self, user, dataset):
        if self.model.completed is not True:
            raise VoltPyNotAllowed('Incomplete procedure.')
        self.__perform(dataset)

    def __perform(self, dataset):
        for cd in dataset.curves_data.all():
            yvec = cd.yVector
            xvec = cd.xVector
            settings = Settings.getData(self.model)
            newyvec = savgol_filter(
                yvec,
                self.model.custom_data['WindowSpan'],
                self.model.custom_data['Degree']
            )
            dataset.updateCurve(self.model, cd, newyvec)
        dataset.save()

    def finalize(self, user):
        settings = Settings.getData(self.model)
        try:
            self.model.custom_data['WindowSpan'] = int(settings['Window Span'])
            self.model.custom_data['Degree'] = int(settings['Degree'])
        except ValueError:
            raise VoltPyFailed('Wrong values for span or degree.')
        self.__perform(self.model.dataset)
        self.model.step = None
        self.model.completed = True
        self.model.save()
        return True
