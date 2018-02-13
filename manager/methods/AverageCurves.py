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
            for cd in self.model.curveSet.curveData.all():
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
            'desc': 'Tag the curves you want to average with the same alphanumeric value.',
        },
    ]
    description = """
This is simple averaging method which allow to calculate the average from
given number of plots.
    """

    @classmethod
    def __str__(cls):
        return "Average Curves"

    def finalize(self, user):
        for k,f in self.model.customData['AveragingData'].items():
            if ( len(f) > 1 ):
                cid = f[0]
                orgcd = self.model.curveSet.curvesData.get(id=cid)
                newcd = deepcopy(orgcd)
                self.model.curveSet.curvesData.remove(orgcd)
                newcd.pk = None
                newcd.id = None
                newcd.date = None
                cnt = 1
                for cid in f[1:]:
                    cd = self.model.curveSet.curvesData.get(id=cid)
                    old = np.dot(newcd.yVector, cnt)
                    newBig = np.add(cd.yVector, old) 
                    newcd.yVector = np.divide(newBig, cnt+1).tolist()
                    cnt += 1
                    self.model.curveSet.curvesData.remove(cd)
                newcd.method = self.__repr__()
                newcd.date = timezone.now()
                newcd.processing = self.model
                newcd.basedOn = orgcd
                newcd.save()
                #TODO: move removal to model ?:
                for a in self.model.curveSet.analytes.all():
                    self.model.curveSet.analytesConc[a.id][newcd.id] = \
                        self.model.curveSet.analytesConc[a.id].get(orgcd.id, 0)
                for cid in f[1:]:
                    for a in self.model.curveSet.analytes.all():
                        self.model.curveSet.analytesConc[a.id].pop(cid, 0)

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

main_class = AverageCurves
