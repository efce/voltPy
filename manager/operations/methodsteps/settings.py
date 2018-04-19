from django import forms
from manager.operations.methodstep import MethodStep


class Settings(MethodStep):
    plot_interaction = 'none'

    class SettingsForm(forms.Form):
        def __init__(self, request, data):
            super(Settings.SettingsForm, self).__init__(request)
            self.data = data
            if data is not None:
                for k, v in data.items():
                    self.fields[k] = forms.CharField(
                        max_length=30,
                        initial=v.get('default', ''),
                        label=k,
                        validators=[v.get('validator', None)]
                    )

    def process(self, user, request, model):
        if request.POST.get('confirm', False) == 'Forward':
            form = self.SettingsForm(request=request.POST, data=self.initial)
            if form.is_valid():
                user_data = {}
                for k, v in self.initial.items():
                    user_data[k] = form.cleaned_data[k]
                model.stepsData['Settings'] = user_data
                model.save()
                return True
            return False
        model.active_step_num = model.active_step_num-1
        model.save()
        return False

    def getHTML(self, user, request, model):
        from django.template import loader
        if request.POST.get('confirm', False) == 'Forward':
            set_form = self.SettingsForm(data=self.initial, request=request.POST)
        else:
            set_form = self.SettingsForm(data=self.initial, request=None)
        template = loader.get_template('manager/form.html')
        context = {
            'form': set_form,
            'submit': 'confirm'
        }
        conf_txt = template.render(
            context=context,
            request=request
        )
        return {'head': '', 'desc': '', 'body': conf_txt}
