from copy import deepcopy
from django.utils import timezone
import manager.methodmanager as mm
import manager.plotmanager as pm
import numpy as np

class OperationSelectFrequency(mm.Operation):
    plot_interaction='none'

    def process(self, user, request, model):
        if ( request.method == 'POST' ):
            tr = float(request.POST['cursor1'])
            model.customData['threshold'] = tr
            model.save()
            return True

    def getHTML(self, user, request, model):
        p = pm.PlotManager()
        for cd in model.curveSet.usedCurveData.all():
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
    _operations = [ 
        {
            'class': OperationSelectFrequency,
            'title': 'Select frequency threshhold.',
            'desc': 'Select frequency treshhold.',
        },
    ]

    def __str__(self):
        return "Low Pass FFT filter"

    def finalize(self, user):
        for cd in self.model.curveSet.usedCurveData.all():
            ylen = len(cd.yVector)
            st = round(self.model.customData['threshold'])
            en = ylen - st - 1;
            ffty = np.fft.fft(cd.yVector)
            ffty[st:en] = [0]*(en-st)
            newcd = deepcopy(cd)
            newcd.id = None
            newcd.pk = None
            iffty = np.fft.ifft(ffty)
            newcd.yVector = np.real(iffty).tolist()
            newcd.method = self.__repr__()
            newcd.date = timezone.now()
            newcd.processing = self.model
            newcd.save()
            self.model.curveSet.usedCurveData.remove(cd)
            self.model.curveSet.usedCurveData.add(newcd)
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
