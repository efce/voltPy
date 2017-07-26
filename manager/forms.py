from django import forms
from .processupload import ProcessUpload
from .models import OnXAxis

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
