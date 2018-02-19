from manager.operations.methodmanager import MethodStep

class SelectPoint(MethodStep):
    plot_interaction = 'set1cursor'

    def process(self, user, request, model):
        data = []
        for cnum in range(1,5):
            name = 'cursor' + str(cnum)
            if request.POST.get(name,''):
                try:
                    data.append(float(request.POST.get(name)))
                except ValueError:
                    continue
        if ( len(data) > 0 ):
            model.stepsData['SelectPoint'] = data[0]
            model.save()
            return True
        return False
