import numpy as np
import manager.operations.method as method
from manager.operations.methodsteps.selectfrequency import SelectFrequency
from manager.exceptions import VoltPyNotAllowed


class FFTLowPass(method.ProcessingMethod):
    can_be_applied = True
    _steps = [
        {
            'class': SelectFrequency,
            'title': 'Select frequency threshhold.',
            'desc': 'Select frequency threshold on the plot and press Forward.',
        },
    ]
    description = """
This is low pass frequency filter used primarily for signal smoothing. The
procedure consists of two steps:
- The signal is transformed to the frequency domain and the power spectrum
  is presented to the user.
- The user selects the cut off threshold, above which the frequencies are
  considered noise.
The procedure automatically removes this frequencies and transforms the
signal back to the original domain.
    """

    @classmethod
    def __str__(cls):
        return "Low Pass FFT filter"

    def __perform(self, dataset):
        for cd in dataset.curves_data.all():
            newcd = cd.getCopy()
            newcdConc = dataset.getCurveConcDict(cd)
            yvec = newcd.yVector
            ylen = len(yvec)
            st = round(self.model.stepsData['SelectFrequency'])
            en = ylen - st + 1
            ffty = np.fft.fft(yvec)
            ffty[st:en] = [0]*(en-st)
            iffty = np.fft.ifft(ffty)
            newcd.yVector = np.real(iffty)
            newcd.save()
            dataset.removeCurve(cd)
            dataset.addCurve(newcd, newcdConc)
        dataset.save()

    def apply(self, user, dataset):
        if self.model.completed is not True:
            raise VoltPyNotAllowed('Incomplete procedure.')
        self.__perform(dataset)

    def finalize(self, user):
        self.__perform(self.model.dataset)
        self.model.step = None
        self.model.completed = True
        self.model.save()
        return True

main_class = FFTLowPass
