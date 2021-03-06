import numpy as np
from overrides import overrides
import manager.operations.method as method
from manager.operations.methodsteps.selecttworanges import SelectTwoRanges
from manager.operations.methodsteps.confirmation import Confirmation
from manager.operations.methodsteps.settings import Settings
from manager.exceptions import VoltPyNotAllowed
from manager.exceptions import VoltPyFailed


class PolynomialBackgroundFit(method.ProcessingMethod):
    can_be_applied = True
    _steps = [
        {
            'class': Settings,
            'title': 'Method settings.',
            'desc': 'Change methods settings.',
        },
        {
            'class': SelectTwoRanges,
            'title': 'Choose two fit intervals.',
            'desc': 'On the plot select two intervals in which polynomial will be fitted and press Forward, or press Back to go to the previous step.',
        },
        {
            'class': Confirmation,
            'title': 'Confirm background shape.',
            'desc': 'Press Forward to subtract the generated baselines or press Back to return to the interval selection.',
        },
    ]
    description = """
The polynomial fit is the most wieldy used baseline correction method,
where the polynomial of the given order is fitted into two intervals -- the first interval 
should be placed before the peak of interest and the second after it.
    """

    @classmethod
    def __str__(cls):
        return "Polynomial Background Fit"

    def process(self, user, request):
        ret = super(PolynomialBackgroundFit, self).process(user, request)
        self.model.custom_data['fitCoeff'] = []
        if self.model.active_step_num == 2:
            for cd in self.model.dataset.curves_data.all():
                ranges = SelectTwoRanges.getData(self.model)
                v = []
                v.append(cd.xValue2Index(ranges[0]))
                v.append(cd.xValue2Index(ranges[1]))
                v.append(cd.xValue2Index(ranges[2]))
                v.append(cd.xValue2Index(ranges[3]))
                v.sort()
                (st1, en1, st2, en2) = (v[0], v[1], v[2], v[3])
                xvec = np.append(cd.xVector[st1:en1], cd.xVector[st2:en2])
                yvec = np.append(cd.yVector[st1:en1], cd.yVector[st2:en2])
                try:
                    degree = int(Settings.getData(self.model)['Degree'])
                except ValueError:
                    raise VoltPyFailed('Wrong degree of polynomial')
                p = np.polyfit(xvec, yvec, degree)
                self.model.custom_data['fitCoeff'].append(p)
                self.model.save()
        return ret

    @overrides
    def initialForStep(self, step_num: int):
        from manager.helpers.validators import validate_polynomial_degree

        if step_num == 0:
            return {
                'Degree': {
                    'default': 3,
                    'validator': validate_polynomial_degree
                }
            }
        return None

    @overrides
    def addToMainPlot(self):
        if self.model.active_step_num == 2:
            fitlines = []
            for cd, fit in zip(self.model.dataset.curves_data.all(), self.model.custom_data['fitCoeff']):
                xvec = cd.xVector
                p = fit
                fitlines.append(dict(
                    x=xvec,
                    y=np.polyval(p, xvec),
                    plottype='line',
                    color='red',
                ))
            return fitlines
        return None

    def apply(self, user, dataset):
        if self.model.completed is not True:
            raise VoltPyNotAllowed('Incomplete procedure.')
        self.__perform(dataset)

    def __perform(self, dataset):
        for cd, fit in zip(dataset.curves_data.all(), self.model.custom_data['fitCoeff']):
            yvec = cd.yVector
            xvec = cd.xVector
            p = fit
            ybkg = np.polyval(p, xvec)
            newyvec = np.subtract(yvec, ybkg)
            dataset.updateCurve(self.model, cd, newyvec)
        dataset.save()

    def finalize(self, user):
        self.__perform(self.model.dataset)
        self.model.step = None
        self.model.completed = True
        self.model.save()
        return True
