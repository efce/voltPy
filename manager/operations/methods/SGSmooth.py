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
Savitzky-Golay smoothing algorithm.
    """

    @classmethod
    def __str__(cls):
        return "SG-Smooth"

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
            newyvec = savgol_filter(
                yvec,
                self.model.customData['WindowSpan'],
                self.model.customData['Degree']
            )
            newcd.yVector = newyvec.tolist()
            newcd.save()
            curveSet.removeCurve(cd)
            curveSet.addCurve(newcd, newcdConc)
        curveSet.save()

    def finalize(self, user):
        try:
            self.model.customData['WindowSpan'] = int(self.model.stepsData['Settings']['Window Span'])
            self.model.customData['Degree'] = int(self.model.stepsData['Settings']['Degree'])
        except ValueError:
            raise VoltPyFailed('Wrong values for span or degree.')
        self.__perform(self.model.curveSet)
        self.model.step = None
        self.model.completed = True
        self.model.save()
        return True

main_class = SGSmooth
