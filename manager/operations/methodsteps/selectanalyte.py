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

    def getHTML(self, user, request, model):
        cs = model.curveSet

        style = "<style>.atOther { display: none; };</style>"
        import manager.analytesTable as at
        at_disp = at.analytesTable(user, cs, objType='cs')

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
        <br />
        Data preview:<br />
        {1}
        """.format(analyte_sel_disp, at_disp)
        return {'head': style, 'desc': '', 'body': txt}

    def process(self, user, request, model):
        cs = model.curveSet

        analyte_sel = self.AnalyteSelectionForm(request.POST, analytes=cs.analytes)
        if analyte_sel.is_valid():
            try:
                analyte = mmodels.Analyte.objects.get(id=analyte_sel.cleaned_data['analyteId'])
            except ObjectDoesNotExist:
                return False
            model.stepsData['SelectAnalyte'] = analyte.id
            model.analytes.add(analyte)
            model.save()
            return True
        else:
            return False
