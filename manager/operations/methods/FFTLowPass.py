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
procedure consists of two steps:<br />
- The signal is transformed to the frequency domain and the power spectrum
  is presented to the user.<br />
- The user selects the cut off threshold, above which the frequencies are
  considered noise.<br />
The procedure automatically removes this frequencies and transforms the
signal back to the original domain.
    """

    @classmethod
    def __str__(cls):
        return "Low Pass FFT filter"

    def __perform(self, dataset):
        for cd in dataset.curves_data.all():
            yvec = cd.yVector
            ylen = len(yvec)
            st = round(SelectFrequency.getData(self))
            en = ylen - st + 1
            ffty = np.fft.fft(yvec)
            ffty[st:en] = [0] * (en - st)
            iffty = np.fft.ifft(ffty)
            newyvec = np.real(iffty)
            dataset.updateCurve(self.model, cd, newyvec)
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
