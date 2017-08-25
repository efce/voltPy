from django import forms
from django.db.models import Q
from django.utils import timezone
from .processupload import ProcessUpload
from .models import *
from .processing import Processing

class UploadFileForm(forms.Form):
    name = forms.CharField(label="Name", max_length=128)
    comment = forms.CharField(label="Comment", max_length=512)
    file = forms.FileField()

    def process(self, user, request):
        p=ProcessUpload(
                user, 
                request.FILES['file'], 
                self.cleaned_data.get('name'),
                self.cleaned_data.get('comment'))
        self.file_id = p.getFileId()
        return p.status


class AddAnalytesForm(forms.Form):
    #TODO: draw plot of file, provide fields for settings analytes 
    isCal = False
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

    def __init__(self, user, view_type, object_id, *args, **kwargs):
        super(AddAnalytesForm, self).__init__(*args, **kwargs)
        if view_type == 'CurveSet' :
            self.isCal = False
            cs = CurveSet.objects.get(id=object_id)
            if not cs.canBeReadBy(user):
                raise 3
            cdata = cs.usedCurveData.all()
            curves_filter_qs = Q()
            for c in cdata:
                curves_filter_qs = curves_filter_qs | Q(id=c.curve.id)
            self.curves = Curve.objects.filter(curves_filter_qs)
        elif view_type == "File":
            cfile = CurveFile.objects.get(id=object_id)
            if not cfile.canBeReadBy(user):
                raise 3
            self.curves = Curve.objects.filter(curveFile=cfile)

        self.generateFields()


    def generateFields(self):
        self.fields['units'] = forms.ChoiceField(choices=self.UNITS)
        curves_filter_qs = Q()
        for c in self.curves:
            curves_filter_qs = curves_filter_qs | Q(curve=c)
        aic = AnalyteInCurve.objects.filter(curves_filter_qs)

        self.fields['analyte'] = forms.CharField(label="Analyte", max_length=128)
        if aic:
            self.fields['analyte'].initial = aic[0].analyte.name
        for c in self.curves:
            ac = aic.filter(curve=c.id)
            if ac:
                self.fields["analyte_%d" % ac[0].id] = forms.FloatField(
                        label = c.name + ":\n" + c.comment , 
                        required = True,
                        initial = ac[0].concentration )
            else:
                self.fields["curve_%d" % c.id] = forms.FloatField(
                        label = c.name + ":\n" + c.comment , 
                        required = True )


    def process(self, user):

        try:
            a = Analyte.objects.get(name=self.cleaned_data.get('analyte'))
        except:
            a = Analyte(name=self.cleaned_data['analyte'])
            a.save()

        for name,val in self.cleaned_data.items():
            if "curve_" in name:
                curve_id = int(name[6:])
                if ( __debug__ ):
                    print("Updateing curve nr: %i with analyte %s, concentration: %s" % (curve_id, a.name, val))
                try:
                    c = Curve.objects.get(id=curve_id)
                    f = CurveFile.objects.get(id=c.curveFile.id)
                except:
                    continue

                if not f.canBeUpdatedBy(user):
                    raise 3

                aic = AnalyteInCurve(analyte=a, curve=c, concentration=float(val))
                aic.save()
            elif "analyte_" in name:
                analyte_in_id= int(name[8:])
                if ( __debug__ ):
                    print("Updateing analyte nr: %i, concentration: %s" % (analyte_in_id, val))
                try:
                    aic = AnalyteInCurve.objects.get(id=analyte_in_id)
                except:
                    continue

                if not aic.canBeUpdatedBy(user):
                    raise 3

                aic.concentration=float(val)
                aic.analyte = a
                aic.save()


class SelectXForm(forms.Form):
    onXAxis = forms.ChoiceField(choices=OnXAxis.AVAILABLE)

    def __init__(self, user, *args, **kwargs):
        self.user = user
        try:
            self.onx = OnXAxis.objects.get(user=self.user)
        except:
            self.onx = OnXAxis(user=user)
            self.onx.save()

        super(SelectXForm, self).__init__(*args, **kwargs)
        self.fields['onXAxis'].initial = self.onx.selected

    def process(self, user):
        self.onx.selected = self.cleaned_data.get('onXAxis')
        self.onx.save()
        return True


class SelectCurvesForCurveSetForm(forms.Form):
    name = forms.CharField(max_length=124, required=True)
    curvesetid = -1

    def __init__(self, user,  *args, **kwargs):
        files = CurveFile.objects.filter(owner=user, deleted=False)
        user_files_filter_qs = Q()
        for f in files:
            user_files_filter_qs = user_files_filter_qs | Q(curveFile=f)
        user_curves = Curve.objects.filter(user_files_filter_qs)

        super(SelectCurvesForCurveSetForm, self).__init__(*args, **kwargs)
        for cb in user_curves:
            self.fields["curve_%d" % cb.id] = forms.BooleanField(
                    label = cb.curveFile.name + ": " + cb.name + (" - %i" % cb.id), 
                    required = False )

    def process(self, user):
        curves = []
        for name,val in self.cleaned_data.items():
            if "curve_" in name:
                if ( val == True ) :
                    curve_id = int(name[6:])
                    c = Curve.objects.get(id=curve_id)
                    if not c.canBeUpdatedBy(user):
                        return False
                    curves.append(c)
        if curves:
            analyte = AnalyteInCurve.objects.filter(curve=curves[0].id)
            if not analyte:
                analyte = None
            else:
                analyte = analyte[0].analyte.name

            cs = CurveSet(
                    owner = user,
                    name = self.cleaned_data['name'],
                    date = timezone.now(),
                    locked = False,
                    deleted = False)
            cs.save()
            self.curvesetid = cs.id
            for c in curves:
                try:
                    cd = CurveData.objects.filter(curve=c)[0]
                    cs.usedCurveData.add(cd)
                except:
                    return False
            cs.save()
            return True


class DeleteFileForm(forms.Form):
    areyousure = forms.BooleanField(label = 'Are you sure?', required=False)

    def __init__(self, file_id,  *args, **kwargs):
        super(DeleteFileForm, self).__init__(*args, **kwargs)
        self.fields['file_id'] = forms.CharField(widget=forms.HiddenInput(),
                initial=file_id)

    def process(self, user, file_id):
        if ( self.cleaned_data['areyousure'] ):
            if ( self.cleaned_data['areyousure'] == True ):
                form_file_id = int(self.cleaned_data['file_id'])
                if ( form_file_id != int(file_id) ):
                    return False
                try:
                    f=CurveFile.objects.get(id=file_id)
                    if f.canBeUpdatedBy(user):
                        f.deleted = True
                        f.save()
                        return True
                    else:
                        return False
                except:
                    return False


class DeleteCurveForm(forms.Form):
    areyousure = forms.BooleanField(label = 'Are you sure?', required=False)

    def __init__(self, curve_id,  *args, **kwargs):
        super(DeleteCurveForm, self).__init__(*args, **kwargs)
        self.fields['curve_id'] = forms.CharField(widget=forms.HiddenInput(),
                initial=file_id)

    def process(self, user, curve_id):
        if ( self.cleaned_data['areyousure'] ):
            if ( self.cleaned_data['areyousure'] == True ):
                try:
                    form_curve_id = int(self.cleaned_data['file_id'])
                    if ( form_curve_id != int(curve_id) ):
                        return False
                    c=Curve.objects.get(id=curve_id)
                    if c.canBeUpdatedBy(user):
                        c.deleted = True
                        c.save()
                        return True
                    else:
                        return False
                except:
                    return False

class SelectRange(forms.Form):
    rangeStart = forms.FloatField(label="Select Start")
    rangeEnd = forms.FloatField(label="Select End")
    def __init__(self, defaultRange, *args, **kwargs):
        super(SelectRange, self).__init__(*args, **kwargs)
        try:
            rangest = defaultRange[0]
            rangend = defaultRange[1]
        except:
            rangest = 0
            rangend = 0
        self.fields['rangeStart'].initial = rangest
        self.fields['rangeEnd'].initial = rangend
        

    def process(self):
        if self.cleaned_data['rangeStart'] < self.cleaned_data['rangeEnd']:
            sel_range = { 
                    'start' : self.cleaned_data['rangeStart'], 
                    'end' : self.cleaned_data['rangeEnd']
                    }
        else:
            sel_range = { 
                    'end' : self.cleaned_data['rangeStart'], 
                    'start' : self.cleaned_data['rangeEnd']
                    }

        return ( sel_range['start'], sel_range['end'] )


#class generateCalibrationForm(forms.Form):
#    #TODO: rethink / rework / add method selection
#
#    def process(self, user, calibration_id):
#        onx = OnXAxis.objects.get(user=user).selected
#        cal = Calibration.objects.get(id=calibration_id)
#        if not cal.canBeUpdatedBy(user):
#            raise 3
#
#        inxstart = 0
#        diffst = float('Inf')
#        inxend = 0
#        diffend = float('Inf')
#        vec = []
#        if ( onx == 'P' ):
#            vec = cal.usedCurveData.all()[0].potential
#        elif (onx == 'T'):
#            vec = cal.usedCurveData.all()[0].time
#        else:
#            vec=range(1,len(cal.usedCurveData.all()[0].probingData))
#            
#        for i,p in enumerate(vec):
#            if abs(p - cal.selectedRange['start']) < diffst:
#                inxstart = i
#                diffst = abs(p-cal.selectedRange['start'])
#            if (abs(p-cal.selectedRange['end']) < diffend):
#                inxend = i
#                diffend = abs(p-cal.selectedRange['end'])
#
#        dataMatrix = {}
#        dataMatrix['x'] = []
#        dataMatrix['y'] = []
#        curveConc = []
#        for cd in cal.usedCurveData.all():
#            aic = AnalyteInCurve.objects.filter(curve=cd.curve) #TODO: and analyte
#            curveConc.append(aic[0].concentration)
#        dataMatrix['x'] = curveConc
#        if ( onx == 'P' or onx == 'T' ):
#            for i,cd in enumerate(cal.usedCurveData.all()):
#                dataMatrix['y'].append(max(cd.current[inxstart:inxend]) - min(cd.current[inxstart:inxend]))
#        else:
#            for i,cd in enumerate(cal.usedCurveData.all()):
#                dataMatrix['y'].append( max(cd.probingData[inxstart:inxend]) - min(cd.probingData[inxstart:inxend]))
#        cal.dataMatrix = dataMatrix;
#        cal.save()
#        p = Processing()
#        p.standardCalibration(cal)
