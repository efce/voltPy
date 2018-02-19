import manager.operations.methodmanager as mm
from django import forms

class TagCurves(mm.MethodStep):
    plot_interaction = 'none'

    class TagCurvesForm(forms.Form):
        def __init__(self, *args, **kwargs):
            self.model = kwargs.pop('model')
            super(TagCurves.TagCurvesForm, self).__init__(*args, **kwargs)
            for cd in self.model.curveSet.curvesData.all():
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
            self.model.customData['TagCurves'] = ret
            self.model.save()

    def process(self, user, request, model):
        print('form process')
        if ( request.method == 'POST'
        and request.POST.get('tagcurvesform', False) != False ):
            form = self.TagCurvesForm(request.POST, model=model)
            print('checking if is valid')
            if form.is_valid():
                print('isa valid')
                form.process()
                return True

    def getHTML(self, user, request, model):
        from django.template import loader
        if ( request.method == 'POST'
        and request.POST.get('tagcurvesform', False) != False ):
            form = self.TagCurvesForm(request.POST, model=model)
            form.is_valid()
        else:
            form = self.TagCurvesForm(model=model)
        template = loader.get_template('manager/form.html')
        context = { 'form': form, 'submit': 'tagcurvesform' }
        return {
            'head': '',
            'body': template.render(
                        context=context,
                        request=request
                    )
        }
