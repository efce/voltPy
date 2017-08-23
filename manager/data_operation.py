from django import forms
from django.utils import timezone
from .models import *
from .method_manager import MethodManager

class DataOperation:

    def __init__(self, **kwargs):
        if ( 'curves' in kwargs ):
            self.operation = 'processing'
            self.curves_ids = kwargs.get('curves').split(",")
            self.curves_ids = [ int(x) for x in self.curves_ids ]
        elif ( 'curveset' in kwargs ):
            self.operation = 'processing'
            self.curveset_id = int(kwargs.get('curveset'))
        elif ( 'analysis' in kwargs ):
            self.operation = 'analysis'
            self.calibration_id = int(kwargs.get('analysis'))
        else:
            raise 33
        self.methodManager = MethodManager()
        self.methodManager.loadMethods()

    def process(self, user, request):
        self.methodManager.process(request)

        return self.methodManager.nextStep()


    def getPage(self):
        if not self.anSelForm:
            return self.methodManager.draw()
        else:
            return self.anSelForm.as_table()


    def getAnalysisSelectForm(self, *args, **kwargs):
        return DataOperation.AnalysisSelectForm(self, *args, **kwargs)


    class AnalysisSelectForm(forms.Form):
        """
        Should not be obtained directly, only by:
        DataOperation.getAnalysisSelectForm
        """
        def __init__(self, parent, *args, **kwargs):
            self.parent = parent
            super(DataOperation.AnalysisSelectForm, self).__init__(*args, **kwargs)
            choices = list(
                            zip(
                                range(0,len(parent.methodManager.getAnalysisMethods())),
                                parent.methodManager.getAnalysisMethods()
                            )
                        )
            self.fields['method'] = forms.ChoiceField(choices=choices, required=True)

        def process(self, user):
            print("csid: %i" % self.parent.curveset_id)
            try:
                cs = CurveSet.objects.get(id=self.parent.curveset_id, owner=user)
            except:
                raise 404
            a = Analysis(
                    owner = user,
                    curveSet = cs,
                    date = timezone.now(),
                    method = self.cleaned_data.get('method'),
                    name = "",
                    step = 0,
                    deleted = False
                )
            a.save()
            return a.id
