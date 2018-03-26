from manager.forms import CursorsForm
from manager.operations.methodstep import MethodStep


class SelectRange(MethodStep):
    plot_interaction = 'set2cursors'

    def process(self, user, request, model):
        cf = CursorsForm(request.POST, cursors_num=2)
        if cf.is_valid():
            cfcd = cf.cleaned_data
            if (len(cfcd) == 2):
                data = []
                for k, v in cfcd.items():
                    try:
                        data.append(float(v))
                    except:
                        return False
                model.stepsData['SelectRange'] = data
                model.save()
                return True
        return False

    def getHTML(self, user, request, model):
        from django.template import loader
        cf = CursorsForm(cursors_num=2)
        template = loader.get_template('manager/form.html')
        context = { 
            'form': cf,
            'submit': 'forward'
        }
        cf_txt = template.render(
            context=context,
            request=request
        )
        return {'head': '', 'desc': '', 'body': cf_txt}
