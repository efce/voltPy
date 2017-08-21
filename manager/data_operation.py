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
        elif ( 'curveset' in kwargs ):
            self.operation = 'processing'
            self.curves = kwargs.get('curveset')
        else:
            raise 33
        self.methodManager = MethodManager()
        self.methodManager.loadMethods()
        self.anSelForm = None

    def process(self, user, request):
        self.methodManager.loadSession(request)
        if ( self.methodManager.selectedMethod == -1 ):
            if ( request.method == 'POST' ):
                self.anSelForm = AnalysisSelectForm(self.methodManager, request)
                if ( self.anSelForm.is_valid() ):
                    form.process(user, self.methodManager, self.curves)
            else:
                self.anSelForm = AnalysisSelectForm(self.methodManager)
        else:
            if ( request.method == 'POST' ):
                pass

    def getPage(self):
        if not self.anSelForm:
            return ""
        else:
            return ""

    def getAnalysisSelectForm(self, *args, **kwargs):
        return AnalysisSelectForm(self.methodManager, *args, **kwargs)


class AnalysisSelectForm(forms.Form):

    def __init__(self, methodManager, *args, **kwargs):
        super(AnalysisSelectForm, self).__init__(*args, **kwargs)
        choices = list (
                        zip(
                            range(0,len(methodManager.getAnalysisMethods())),
                            methodManager.getAnalysisMethods()
                        )
                    )
        self.fields['method'] = forms.ChoiceField(choices=choices, required=True)

    def process(self, user, methodManager, curveset_id):
        try:
            c = CurveSet.objects.get(id=curveset_id)
        except:
            raise 404
        a = Analysis(
                owner = user,
                curveSet = c,
                date = timezone.now(),
                method = methodManager.getAnalysisMethods()[self.cleaned_data.get('method')],
                name = "",
                complete=False,
                deleted = False
            )
        a.save()
        return a.id
