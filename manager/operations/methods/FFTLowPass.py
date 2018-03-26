import numpy as np
import manager.operations.method as method
from manager.operations.methodsteps.selectfrequency import SelectFrequency


class FFTLowPass(method.ProcessingMethod):
    _steps = [ 
        {
            'class': SelectFrequency,
            'title': 'Select frequency threshhold.',
            'desc': 'Select frequency treshhold and press Forward, or press Back to change the selection.',
        },
    ]
    description = """
This is low pass frequency filter used primarly for signal smoothing. The
procedure consists of two steps:
- The signal is transformed to the frequency domain and the power spectrum
  is presented to the user.
- The user selects the cut off treshold, above which the frequences are
  considered noise.
The procedure automatically removes this frequencies and transforms the
signal back to the original domain.
    """

    @classmethod
    def __str__(cls):
        return "Low Pass FFT filter"

    def finalize(self, user):
        cs = self.model.curveSet
        for cd in cs.curvesData.all():
            newcd = cd.getCopy()
            newcdConc = cs.getCurveConcDict(cd)
            yvec = newcd.yVector
            ylen = len(yvec)
            st = round(self.model.stepsData['SelectFrequency'])
            en = ylen - st + 1
            ffty = np.fft.fft(yvec)
            ffty[st:en] = [0]*(en-st)
            iffty = np.fft.ifft(ffty)
            newcd.yVector = np.real(iffty).tolist()
            newcd.save()
            cs.removeCurve(cd)
            cs.addCurve(newcd, newcdConc)
        cs.save()
        self.model.step = None
        self.model.completed = True
        self.model.save()
        return True

    def getInfo(self, request, user):
        return {
            'head': '',
            'body': ''
        }

main_class = FFTLowPass
