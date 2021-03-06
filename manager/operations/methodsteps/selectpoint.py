from manager.forms import CursorsForm
from manager.operations.methodstep import MethodStep


class SelectPoint(MethodStep):
    plot_interaction = 'set1cursor'

    def process(self, request, user, model):
        cf = CursorsForm(request.POST, cursors_num=1)
        if cf.is_valid():
            cfcd = cf.cleaned_data
            if (len(cfcd) == 1):
                data = None
                for k, v in cfcd.items():
                    try:
                        data = float(v)
                    except:
                        return False
                if data is None:
                    return False
                model.steps_data['SelectPoint'] = data 
                model.save()
                return True
        return False

    def getHTML(self, request, user, model):
        from django.template import loader
        cf = CursorsForm(cursors_num=1)
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
