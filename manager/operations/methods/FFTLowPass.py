from copy import deepcopy
import numpy as np
from django.utils import timezone
import manager.operations.methodmanager as mm
import manager.plotmanager as pm

class StepSelectFrequency(mm.MethodStep):
    plot_interaction='none'

    def process(self, user, request, model):
        if ( request.method == 'POST' ):
            tr = float(request.POST['cursor1'])
            model.customData['threshold'] = tr
            model.save()
            return True

    def getHTML(self, user, request, model):
        p = pm.PlotManager()
        for cd in model.curveSet.curvesData.all():
            ylen = len(cd.yVector)
            newy = np.absolute(np.fft.fft(cd.yVector))
            newy = newy[1:round(ylen/2.0)].tolist()
            p.add(
                y=newy,
                x=range(round(ylen/2)),
                plottype='line',
                color='red'
            )
        
        p.setInteraction('set1cursor')
        p.include_x_switch = True
        src,div = p.getEmbeded(request, user, 'processing', model.id)
        return { 'head': src, 'body' : div }

class FFTLowPass(mm.ProcessingMethod):
    _steps = [ 
        {
            'class': StepSelectFrequency,
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
        for cd in self.model.curveSet.curvesData.all():
            ylen = len(cd.yVector)
            st = round(self.model.customData['threshold'])
            en = ylen - st - 1;
            ffty = np.fft.fft(cd.yVector)
            ffty[st:en] = [0]*(en-st)
            newcd = deepcopy(cd)
            newcd.id = None
            newcd.pk = None
            newcd.date = None
            iffty = np.fft.ifft(ffty)
            newcd.yVector = np.real(iffty).tolist()
            newcd.method = self.__repr__()
            newcd.date = timezone.now()
            newcd.processing = self.model
            newcd.basedOn = cd
            newcd.save()
            for a in self.model.curveSet.analytes.all():
                self.model.curveSet.analytesConc[a.id][newcd.id] = \
                    self.model.curveSet.analytesConc[a.id].pop(cd.id, 0)
            self.model.curveSet.curvesData.remove(cd)
            self.model.curveSet.curvesData.add(newcd)
        self.model.curveSet.save()
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
