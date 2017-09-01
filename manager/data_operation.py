from django import forms
from django.utils import timezone
from django.http import HttpResponseRedirect
from django.http import HttpResponse
from django.template import loader
from django.core.urlresolvers import reverse
from .models import *
from .method_manager import MethodManager
from .plotmaker import PlotMaker

class DataOperation:
    """
    This class is used to streamline the usage of MethodManager.
    """
    def __init__(self, **kwargs):
        if ( 'curveset' in kwargs ):
            self.operation = 'other'
            self.curveset_id = int(kwargs.get('curveset'))
        elif ( 'processing' in kwargs ):
            self.operation = 'processing'
            self.processing_id = int(kwargs.get('processing'))
            try:
                self.processing = Processing.objects.get(id=self.processing_id)
                self.curveset_id = self.processing.curveSet.id
            except:
                raise 404
        elif ( 'analysis' in kwargs ):
            self.operation = 'analysis'
            self.analysis_id = int(kwargs.get('analysis'))
            try:
                self.analysis = Analysis.objects.get(id=self.analysis_id)
            except:
                raise 404
        else:
            raise 33
        self.methodManager = MethodManager()
        self.methodManager.loadMethods()
        if ( self.operation == 'analysis' ):
            self.methodManager.setAnalysis(self.analysis)
        elif ( self.operation == 'processing' ):
            self.methodManager.setProcessing(self.processing)


    def process(self, user, request):
        self.methodManager.process(user, request)

    def getInfo(self):
        return self.methodManager.getInfo()


    def getContent(self, user):
        if self.methodManager.redirect:
            return HttpResponseRedirect( self.methodManager.redirect )

        template = loader.get_template('manager/analyze.html')
        context = {
                'analyze_content': self.methodManager.getContent(),
                'user': user,
                'analysis_id': self.analysis_id,
                'curveset_id': Analysis.objects.get(id=self.analysis_id).curveSet.id,
                'plot_width' : PlotMaker.plot_width,
                'plot_height' : PlotMaker.plot_height
                }
        return HttpResponse(template.render(context))


    def getAnalysisSelectForm(self, *args, **kwargs):
        return DataOperation.AnalysisSelectForm(self, *args, **kwargs)


    def getProcessingSelectForm(self, *args, **kwargs):
        return DataOperation.ProcessingSelectForm(self, *args, **kwargs)


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
                                [ str(x) for x in
                                    parent.methodManager.getAnalysisMethods() ],
                                parent.methodManager.getAnalysisMethods()
                            )
                        )

            self.fields['method'] = forms.ChoiceField(
                    choices=choices,
                    required=True, 
                    label='Analysis method')

        def process(self, user):
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

    class ProcessingSelectForm(forms.Form):
        """
        Should not be obtained directly, only by:
        DataOperation.getProcessingSelectForm
        """
        def __init__(self, parent, *args, **kwargs):
            self.parent = parent
            super(DataOperation.ProcessingSelectForm, self).__init__(*args, **kwargs)
            choices = list(
                            zip(
                                [ str(x) for x in
                                    parent.methodManager.getProcessingMethods() ],
                                parent.methodManager.getProcessingMethods()
                            )
                        )

            self.fields['method'] = forms.ChoiceField(
                    choices=choices,
                    required=True, 
                    label='Processing method')

        def process(self, user):
            try:
                cs = CurveSet.objects.get(id=self.parent.curveset_id, owner=user)
            except:
                raise 404
            a = Processing(
                    owner = user,
                    curveSet = cs,
                    date = timezone.now(),
                    method = self.cleaned_data.get('method'),
                    name = "",
                    step = 0,
                    deleted = False,
                    completed = False
                )
            a.save()
            return a.id
