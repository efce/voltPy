from django import forms
from manager.operations.methodstep import MethodStep


class Settings(MethodStep):
    plot_interaction = 'none'

    class SettingsForm(forms.Form):
        def __init__(self, *args, **kwargs):
            initial_data = kwargs.pop('initial', {})
            super(Settings.SettingsForm, self).__init__(*args, **kwargs)
            if initial_data:
                for k, v in initial_data.items():
                    self.fields[k] = forms.CharField(
                        max_length=30,
                        initial=v.get('default', ''),
                        label=k,
                        validators=[v['validator']] if v.get('validator', False) else None
                    )

    def process(self, user, request, model):
        if request.POST.get('confirm', False) == 'Forward':
            form = self.SettingsForm(request.POST, initial=self.initial)
            if form.is_valid() is True:
                user_data = {}
                for k, v in self.initial.items():
                    user_data[k] = form.cleaned_data[k]
                model.steps_data['Settings'] = user_data
                model.save()
                return True
            return False
        model.active_step_num = model.active_step_num-1
        model.save()
        return False

    def getHTML(self, user, request, model):
        from django.template import loader
        if request.POST.get('confirm', False) == 'Forward':
            set_form = self.SettingsForm(request.POST, initial=self.initial)
        else:
            set_form = self.SettingsForm(initial=self.initial)
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
