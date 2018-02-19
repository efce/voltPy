from manager.operations.methodmanager import MethodStep

class Confirmation(MethodStep):
    plot_interaction = 'confirm'

    def process(self, user, request, model):
        if request.POST.get('command', False) == 'confirm':
            return True
        else:
            model.active_step_num = model.active_step_num-1
            model.save()
            return False

