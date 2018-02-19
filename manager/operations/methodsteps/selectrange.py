from manager.operations.methodmanager import MethodStep

class SelectRange(MethodStep):
    plot_interaction = 'set2cursors'

    def process(self, user, request, model):
        data = []
        for cnum in range(1,5):
            name = 'cursor' + str(cnum)
            if request.POST.get(name,''):
                try:
                    data.append(float(request.POST.get(name)))
                except ValueError:
                    continue
        if (len(data) == 2):
            model.customData['range1'] = data
            model.save()
            return True
        return False
