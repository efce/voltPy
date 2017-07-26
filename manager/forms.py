from django import forms
from django.db.models import Q
from .processupload import ProcessUpload
from .models import OnXAxis, CurveFile, CurveBasic

class UploadFileForm(forms.Form):
    name = forms.CharField(label="Name", max_length=128)
    comment = forms.CharField(label="Comment", max_length=512)
    file = forms.FileField()

    def process(self, user_id, request):
        p=ProcessUpload(
                user_id, 
                request.FILES['file'], 
                request.POST['name'],
                request.POST['comment'])
        return p.status


class AddAnalytesForms(forms.Form):
    #TODO: draw plot of file, provide fields for settings analytes 
    pass


class SelectXForm(forms.Form):
    onXAxis = forms.ChoiceField(choices=OnXAxis.AVAILABLE)

    def __init__(self, user_id, *args, **kwargs):
        self.user_id = user_id
        try:
            self.onx = OnXAxis.objects.get(user=self.user_id)
        except:
            self.onx = OnXAxis(user=user_id)
            self.onx.save()

        super(SelectXForm, self).__init__(*args, **kwargs)
        self.fields['onXAxis'].initial = self.onx.selected
    
    def process(self, user_id, request):
        self.onx.selected = request.POST['onXAxis']
        self.onx.save()
        return True

class SelectCurvesForCalibrationForm(forms.Form):
    def __init__(self, user_id,  *args, **kwargs):
        files = CurveFile.objects.filter(owner=user_id)
        user_files_filter_qs = Q()
        for f in files:
            user_files_filter_qs = user_files_filter_qs | Q(curveFile=f)
        user_curves = CurveBasic.objects.filter(user_files_filter_qs)

        super(SelectCurvesForCalibrationForm, self).__init__(*args, **kwargs)
        for cb in user_curves:
            self.fields["curve%d" % cb.id] = forms.BooleanField(
                    label = cb.curveFile.name + ": " + cb.name + (" - %i" % cb.id), 
                    #attrs={'class': 'file' + cb.curveFile.name},
                    required = False )

    def process(self, user_id, request):
        pass

