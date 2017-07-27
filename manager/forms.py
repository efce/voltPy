from django import forms
from django.db.models import Q
from .processupload import ProcessUpload
from .models import OnXAxis, CurveFile, Curve, Analyte, AnalyteInCurve

class UploadFileForm(forms.Form):
    name = forms.CharField(label="Name", max_length=128)
    comment = forms.CharField(label="Comment", max_length=512)
    file = forms.FileField()

    def process(self, user_id, request):
        p=ProcessUpload(
                user_id, 
                request.FILES['file'], 
                self.cleaned_data.get('name'),
                self.cleaned_data.get('comment'))
        self.file_id = p.getFileId()
        return p.status


class AddAnalytesForm(forms.Form):
    #TODO: draw plot of file, provide fields for settings analytes 
    analyte = forms.CharField(label="Analyte", max_length=128)
    UNITS = (
            ('ng/L','ng/L'),
            ('µg/L','µg/L'),
            ('mg/L','mg/L'),
            ('g/L' ,'g/L'  ),
            ('nM'  ,'nM'  ),
            ('µM'  ,'µM'  ),
            ('mM'  ,'mM'  ),
            ( 'M'  , 'M'  )
            )

    def __init__(self, user_id, file_id, *args, **kwargs):
        super(AddAnalytesForm, self).__init__(*args, **kwargs)
        cfile = CurveFile.objects.get(pk=file_id)
        print(cfile.owner.id)
        if ( cfile.owner.id != int(user_id) ):
            raise 3
        curves = Curve.objects.filter(curveFile=cfile)
        self.fields['units'] = forms.ChoiceField(choices=self.UNITS)
        for c in curves:
            self.fields["curve%d" % c.id] = forms.CharField(
                    max_length=16,
                    label = c.name + ":\n" + c.comment , 
                    #attrs={'class': 'file' + cb.curveFile.name},
                    required = False )

    def process(self, user_id):
        try:
            a = Analyte.objects.get(name=self.cleaned_data.get('analyte'))
        except:
            a = Analyte(name=self.cleaned_data['analyte'])
            a.save()

        for name,val in self.cleaned_data.items():
            if "curve" not in name:
                continue
            curve_id = int(name[5:])
            if ( __debug__ ):
                print("Updateing curve nr: %i with analyte %s, concentration: %s" % (curve_id, a.name, val))
            try:
                c = Curve.objects.get(pk=curve_id)
                f = CurveFile.objects.get(pk=c.curveFile)
            except:
                continue

            if f.owner.id != int(user_id):
                raise 3

            aic = AnalyteInCurve(analyte=a, curve=c, concentration=double(value))
            aic.save()


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

    def process(self, user_id):
        self.onx.selected = self.cleaned_data.get('onXAxis')
        self.onx.save()
        return True

class SelectCurvesForCalibrationForm(forms.Form):
    def __init__(self, user_id,  *args, **kwargs):
        files = CurveFile.objects.filter(owner=user_id)
        user_files_filter_qs = Q()
        for f in files:
            user_files_filter_qs = user_files_filter_qs | Q(curveFile=f)
        user_curves = Curve.objects.filter(user_files_filter_qs)

        super(SelectCurvesForCalibrationForm, self).__init__(*args, **kwargs)
        for cb in user_curves:
            self.fields["curve%d" % cb.id] = forms.BooleanField(
                    label = cb.curveFile.name + ": " + cb.name + (" - %i" % cb.id), 
                    #attrs={'class': 'file' + cb.curveFile.name},
                    required = False )

    def process(self, user_id, request):
        pass

