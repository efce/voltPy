from copy import deepcopy
from django.utils import timezone
import manager.methodmanager as mm
import numpy as np
import django.forms as forms


class OperationAverage(mm.Operation):
    plot_interaction = 'none'

    class AveragingForm(forms.Form):
        def __init__(self, *args, **kwargs):
            self.model = kwargs.pop('model')
            super(OperationAverage.AveragingForm, self).__init__(*args, **kwargs)
            for cd in self.model.curveSet.usedCurveData.all():
                self.fields['cd'+str(cd.id)] = forms.CharField(
                    max_length=4, 
                    initial='',
                    label=''.join([cd.curve.name, ' ', cd.curve.comment]),
                    required=False
                )

        def process(self):
            ret = {}
            for k,f in self.cleaned_data.items():
                if k.startswith('cd'):
                    if f.strip() == '':
                        continue
                    cid = int(k[2:])
                    kentry = ret.get(f,[])
                    kentry.append(cid)
                    ret[f] = kentry
            self.model.customData['AveragingData'] = ret
            self.model.save()

    def process(self, user, request, model):
        print('form process')
        if ( request.method == 'POST'
        and request.POST.get('avform', False) != False ):
            form = self.AveragingForm(request.POST, model=model)
            print('checking if is valid')
            if form.is_valid():
                print('isa valid')
                form.process()
                return True

    def getHTML(self, user, request, model):
        from django.template import loader
        if ( request.method == 'POST'
        and request.POST.get('avform', False) != False ):
            form = self.AveragingForm(request.POST, model=model)
            form.is_valid()
        else:
            form = self.AveragingForm(model=model)
        template = loader.get_template('manager/form.html')
        context = { 'form': form, 'submit': 'avform' }
        return { 
            'head': '', 
            'body': template.render(
                        context=context,
                        request=request
                    ) 
        }

class AverageCurves(mm.ProcessingMethod):
    _operations = [ 
        {
            'class': OperationAverage,
            'title': 'Averaging',
            'desc': 'Set the same alphanumeric value to the curves you want to average.',
        },
    ]

    def __str__(self):
        return "Average Curves"

    def finalize(self, user):
        for k,f in self.model.customData['AveragingData'].items():
            if ( len(f) > 1 ):
                cid = f[0]
                orgcd = self.model.curveSet.usedCurveData.get(id=cid)
                newcd = deepcopy(orgcd)
                self.model.curveSet.usedCurveData.remove(orgcd)
                newcd.pk = None
                newcd.id = None
                cnt = 1
                for cid in f[1:]:
                    #running average to prevent overflows
                    cd = self.model.curveSet.usedCurveData.get(id=cid)
                    old = np.dot(newcd.yVector, cnt)
                    newBig = np.add(cd.yVector, old) 
                    newcd.yVector = np.divide(newBig, cnt+1).tolist()
                    cnt += 1
                    self.model.curveSet.usedCurveData.remove(cd)
                newcd.method = self.__repr__()
                newcd.date = timezone.now()
                newcd.processing = self.model
                newcd.save()
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

main_class = AverageCurves
