from manager.operations.methodmanager import MethodStep
from manager.forms import CursorsForm
import manager.plotmanager as pm
import numpy as np
import math

class SelectFrequency(MethodStep):
    plot_interaction='none'

    def process(self, user, request, model):
        cf = CursorsForm(request.POST, cursors_num=1)
        if cf.is_valid():
            cfcd = cf.cleaned_data
            if (len(cfcd) == 1):
                data = None
                for k,v in cfcd.items():
                    try:
                        data = float(v)
                    except:
                        return False
                if data is None:
                    return False
                model.stepsData['SelectFrequency'] = data 
                model.save()
                return True
        return False

    def getHTML(self, user, request, model):
        from django.template import loader
        cf = CursorsForm(cursors_num=1)
        template = loader.get_template('manager/form.html')
        context = { 
            'form': cf, 
            'submit': 'forward' 
        }
        cf_txt = template.render(
            context=context,
            request=request
        )
        p = pm.PlotManager()
        for cd in model.curveSet.curvesData.all():
            ylen = len(cd.yVector)
            newy = np.absolute(np.fft.fft(cd.yVector))
            newy = newy[:round(ylen/2.0)].tolist()
            p.add(
                y=newy,
                x=range(math.floor(ylen/2)),
                plottype='line',
                color='red'
            )
        
        p.setInteraction('set1cursor')
        p.include_x_switch = True
        src,div = p.getEmbeded(request, user, 'processing', model.id)
        return { 'head': src, 'body' : ' '.join((div, cf_txt)) }

