from django import forms
from manager.operations.methodstep import MethodStep


class Confirmation(MethodStep):
    plot_interaction = 'none'

    class ConfirmForm(forms.Form):
        pass

    def process(self, user, request, model):
        if request.POST.get('confirm', False) == 'Forward':
            return True
        else:
            model.active_step_num = model.active_step_num-1
            model.save()
            return False

    def getHTML(self, user, request, model):
        from django.template import loader
        conf_form = self.ConfirmForm()
        template = loader.get_template('manager/form.html')
        context = { 
            'form': conf_form,
            'submit': 'confirm'
        }
        conf_txt = template.render(
            context=context,
            request=request
        )
        return {'head': '', 'desc': '', 'body': conf_txt}
