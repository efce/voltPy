from .method_manager import MethodManager
from django import forms

class DataOperation:

    def __init__(self, **kwargs):
        if ( 'curves' in kwargs ):
            self.operation = 'processing'
            self.curves = kwargs.get('curves')
        elif ( 'curveset' in kwargs ):
            self.operation = 'processing'
            self.curves = kwargs.get('curveset')
        elif ( 'calibration' in kwargs ):
            self.operation = 'analysis'
            self.calibration = kwargs.get('calibration')
        else:
            raise 33
        self.methodManager = MethodManager()
        self.methodManager.loadMethods()
        self.anSelForm = None

    def process(self, user, request):
        if not self.methodManager.isMethodSelected():
            if ( request.method == 'POST' ):
                self.anSelForm = AnalysisSelectForm(self.methodManager, request)
                if ( self.anSelForm.is_valid() ):
                    analysisid = self.anSelForm.process(user, self.methodManager, self.curves)
                    if analysisid and analysisid > -1:
                        pass
                        #return HttpRedirect
            else:
                self.anSelForm = AnalysisSelectForm(self.methodManager)
            return True
        # Else use the selected method settings:
        else:
            self.methodManager.process(request)
            # Reurn False when processing/analysis complete
            return self.methodManager.nextStep()


    def getPage(self):
        if not self.anSelForm:
            return self.methodManager.draw()
        else:
            return self.anSelForm.as_table()

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
                step = 0,
                deleted = False
            )
        a.save()
        return a.id
