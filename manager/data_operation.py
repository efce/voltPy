from .method_manager import MethodManager
from django import forms

class DataOperation:

    def __init__(self, **kwargs):
        if ( 'curves' in kwargs ):
            self.operation = 'processing'
            self.curves = kwargs.get('curves')
        elif ( 'calibration' in kwargs ):
            self.operation = 'analysis'
            self.calibration = kwargs.get('calibration')
        else:
            raise 33
        self.methodManager = MethodManager()
        self.methodManager.load()


    def draw(self, calid, request):
        if ( self.methodManager.selectedMethod == -1 ):
            if ( request.method == 'POST' ):
                form = ProcessingSelectForm(self.methodManager, request)
                if ( form.is_valid() ):
                    form.process(calid)
            else:
                form = ProcessingSelectForm(self.methodManager)
        else:
            if ( request.method == 'POST' ):
                pass

    def getProcessingSelectForm(self, *args, **kwargs):
        return ProcessingSelectForm(self.methodManager, *args, **kwargs)


class ProcessingSelectForm(forms.Form):

    def __init__(self, methodManager, *args, **kwargs):
        super(ProcessingSelectForm, self).__init__(*args, **kwargs)
        print("methods:")
        print(methodManager.getAnalysisMethods())
        choices = list (
                        zip(
                            range(0,len(methodManager.getAnalysisMethods())),
                            methodManager.getAnalysisMethods()
                        )
                    )
        print(choices)
        self.fields['method'] = forms.ChoiceField(choices=choices, required=True)

    def process(self, methodManager, calid):
        try:
            c = Calibration.objects.get(id=calid)
        except:
            return
        c.method=methodManager.getAnalysisMethods()[self.cleaned_data.get('method')]
