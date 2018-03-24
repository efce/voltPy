from django import forms
from django.template import loader
import manager.operations.methodstep as ms


class TagCurves(ms.MethodStep):
    plot_interaction = 'none'

    class TagCurvesForm(forms.Form):
        def __init__(self, *args, **kwargs):
            self.model = kwargs.pop('model')
            initialTags = kwargs.pop('initial', {})
            if initialTags is None:
                initialTags = {}
            super(TagCurves.TagCurvesForm, self).__init__(*args, **kwargs)
            for cd in self.model.curveSet.curvesData.all():
                self.fields['cd%d' % cd.id] = forms.CharField(
                    max_length=4, 
                    initial=initialTags.get(cd.id, ''),
                    label=''.join([cd.curve.name, ' ', cd.curve.comment]),
                    required=True
                )
                self.fields['cd%d' % cd.id].widget.attrs['class'] = ' '.join([
                    '_voltJS_plotHighlightInput',
                    '_voltJS_highlightCurve@%d' % cd.id,
                ])

        def process(self):
            ret = {}
            for k, f in self.cleaned_data.items():
                if k.startswith('cd'):
                    if f.strip() == '':
                        continue
                    cid = int(k[2:])
                    kentry = ret.get(f, [])
                    kentry.append(cid)
                    ret[f] = kentry
            self.model.stepsData['TagCurves'] = ret
            self.model.save()

    def process(self, user, request, model):
        if all([
            request.method == 'POST',
            request.POST.get('tagcurvesform', False) is not False
        ]):
            form = self.TagCurvesForm(request.POST, model=model, initial=self.initial)
            if form.is_valid():
                form.process()
                return True

    def getHTML(self, user, request, model):
        if all([
            request.method == 'POST',
            request.POST.get('tagcurvesform', False) is not False
        ]):
            form = self.TagCurvesForm(request.POST, model=model, initial=self.initial)
            form.is_valid()
        else:
            form = self.TagCurvesForm(model=model, initial=self.initial)
        template = loader.get_template('manager/form.html')
        context = {'form': form, 'submit': 'tagcurvesform'}
        return {
            'head': '',
            'body': template.render(
                        context=context,
                        request=request
                    )
        }
