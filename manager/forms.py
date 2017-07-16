from django import forms
from .processupload import ProcessUpload

class UploadFileForm(forms.Form):
    name = forms.CharField(label="Name", max_length=128)
    comment = forms.CharField(label="Comment", max_length=512)
    file = forms.FileField()

    def process(self, user_id, request):
        p=ProcessUpload(user_id, request.FILES['file'], request.POST['name'], request.POST['comment'])
        return p.status
