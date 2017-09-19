from copy import deepcopy
from django.utils import timezone
import manager.methodmanager as mm
import numpy as np
import django.forms as forms

class OperationAverage(mm.Operation):
    plot_interaction = 'none'

    def process(self, user, request, model):
        if ( request.method == 'POST'
        and request.POST.get('avform', False) != False ):
            form = AveragingForm(model, request)
            if form.is_valid():
                form.process()
                return True

    def getHTML(self, user, request, model):
        from django.template import loader
        if ( request.method == 'POST'
        and request.POST.get('avform', False) != False ):
            form = AveragingForm(model, request)
        else:
            form = AveragingForm(model)
        template = loader.get_template('manager/form.html')
        context = { 'form': form, 'submit': 'avform' }
        return { 'head': '', 'body': template.render(context, request) }

class AveragingForm(forms.Form):
    def __init__(self, model, *args, **kwargs):
        super(AveragingForm, self).__init__(*args, **kwargs)
        for cd in model.curveSet.usedCurveData.all():
            self.fields['cd'+str(cd.id)] = forms.CharField(
                max_length=4, 
                initial='',
                label=cd.curve.name + ' ' + cd.curve.comment,
                required = False
            )

    def process(self, model):
        ret = {}
        for k,f in self.cleaned_data.items():
            if k.startswith('cd'):
                if f.strip() == '':
                    continue
                cid = int(k[2:])
                kentry = ret.get(f,[])
                kentry.append(cid)
        self.model.customData['AveragingData'] = ret
        self.model.save()

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
        return True

    def getInfo(self, request, user):
        return {
            'head': '',
            'body': ''
        }

main_class = AverageCurves
