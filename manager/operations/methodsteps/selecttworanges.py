from manager.forms import CursorsForm
from manager.operations.methodstep import MethodStep


class SelectTwoRanges(MethodStep):
    plot_interaction = 'set4cursors'

    def process(self, user, request, model):
        cf = CursorsForm(request.POST, cursors_num=4)
        if cf.is_valid():
            cfcd = cf.cleaned_data
            if (len(cfcd) == 4):
                data = []
                for k, v in cfcd.items():
                    try:
                        data.append(float(v))
                    except:
                        return False
                data.sort()
                model.stepsData['SelectTwoRanges'] = data
                model.save()
                return True
        return False

    def getHTML(self, user, request, model):
        from django.template import loader
        cf = CursorsForm(cursors_num=4)
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
