from django.core.exceptions import ObjectDoesNotExist
from django import forms
from manager.operations.methodstep import MethodStep
import manager.models as mmodels


class SelectAnalyte(MethodStep):
    plot_interaction = 'none'

    class AnalyteSelectionForm(forms.Form):
        def __init__(self, *args, **kwargs):
            analytes = kwargs.pop('analytes', [])
            super(SelectAnalyte.AnalyteSelectionForm, self).__init__(*args, **kwargs)
            choices = zip(
                [-1] + [x.id for x in analytes.all()],
                ['Select'] + [x.name for x in analytes.all()]
            )
            self.fields['analyteId'] = forms.ChoiceField(
                choices=choices,
                initial=-1,
                label='Analyte'
            )
            self.fields['analyteId'].widget.attrs['class'] = '_voltJS_ChangeDispValue'

    def getHTML(self, request, user, model):
        cs = model.dataset

        style = "<style>.at_hideable { display: none !important; };</style>"
        import manager.analytesTable as at
        at_disp = at.analytesTable(cs, obj_type='dataset')

        analyte_sel = self.AnalyteSelectionForm(analytes=cs.analytes)
        from django.template import loader
        template = loader.get_template('manager/form.html')
        context = {'form': analyte_sel, 'submit': 'selectAnalyte'}
        analyte_sel_disp = template.render(
            context=context,
            request=request
        )
        txt = """
        {0}
        <p style="margin-bottom: 10px;">Data preview:</p>
        {1}
        """.format(analyte_sel_disp, at_disp)
        return {'head': style, 'desc': '', 'body': txt}

    def process(self, request, user, model):
        cs = model.dataset

        analyte_sel = self.AnalyteSelectionForm(request.POST, analytes=cs.analytes)
        if analyte_sel.is_valid():
            try:
                analyte = mmodels.Analyte.objects.get(id=analyte_sel.cleaned_data['analyteId'])
            except ObjectDoesNotExist:
                return False
            model.steps_data['SelectAnalyte'] = analyte.id
            model.analytes.add(analyte)
            model.save()
            return True
        else:
            return False
