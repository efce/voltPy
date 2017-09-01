from django import forms
from django.db.models import Q
from django.utils import timezone
from .processupload import ProcessUpload
from .models import *

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

        super(SelectCurvesForCurveSetForm, self).__init__(*args, **kwargs)
        order = ['name']

        self.fields['FILES'] = forms.CharField(
                label='',
                initial='Files:')
        self.fields['FILES'].widget.attrs['readonly'] = True
        order.append('FILES')
        for f in files:
            fname = 'curveFile_{0}'.format(f.id)
            self.fields[fname] = \
                    forms.BooleanField(label=f,required=False)
            self.fields[fname].widget.attrs['class'] = 'parent'
            order.append(fname)
            cf = Curve.objects.filter(curveFile=f)
            for c in cf:
                cname = "curve_{0}_curveFile_{1}".format(c.id,f.id)
                self.fields[cname] = \
                        forms.BooleanField(label = c, required = False )
                self.fields[cname].widget.attrs['class'] = 'child'
                order.append(cname)
            self.fields['end_'+fname] = forms.CharField( label='', initial='')
            self.fields['end_'+fname].widget.attrs['readonly'] = True
            self.fields['end_'+fname].widget.attrs['class'] = 'invisible'
            order.append('end_'+fname)

        css = CurveSet.objects.filter(owner=user, deleted=False)
        self.fields['CURVESETS'] = forms.CharField(
                label='',
                initial='Curve Sets:')
        self.fields['CURVESETS'].widget.attrs['readonly'] = True
        order.append('CURVESETS')
        for cs in css:
            csname = 'curveSet_{0}'.format(cs.id)
            self.fields[csname] = \
                    forms.BooleanField(
                            label=cs,
                            help_text='asdasdasd',
                            required=False)
            self.fields[csname].widget.attrs['class'] = 'parent'

            order.append(csname)
            for c in cs.usedCurveData.all():
                cname = "curveData_{0}_curveSet_{1}".format(c.id,cs.id)
                self.fields[cname] = \
                        forms.BooleanField(label = c.curve, required = False )
                self.fields[cname].widget.attrs['class'] = 'child'
                order.append(cname)
            self.fields['end_'+csname] = forms.CharField( label='', initial='')
            self.fields['end_'+csname].widget.attrs['readonly'] = True
            self.fields['end_'+csname].widget.attrs['class'] = 'invisible'
            order.append('end_'+csname)
        self.order_fields(order)


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


class DeleteForm(forms.Form):
    areyousure = forms.BooleanField(label = 'Are you sure?', required=False)

    def __init__(self, item,  *args, **kwargs):
        super(DeleteForm, self).__init__(*args, **kwargs)
        self.fields['item_id'] = forms.CharField(
                widget=forms.HiddenInput(),
                initial=item.id)

    def process(self, user, item):
        if ( self.cleaned_data['areyousure'] ):
            if ( self.cleaned_data['areyousure'] == True ):
                form_item_id = int(self.cleaned_data['item_id'])
                if ( form_item_id != int(item.id) ):
                    return False
                try:
                    if item.canBeUpdatedBy(user):
                        item.deleted = True
                        item.save()
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


class SelectPoint(forms.Form):
    point = forms.FloatField(label="Value")
    def __init__(self, defaultRange, *args, **kwargs):
        super(SelectPoint, self).__init__(*args, **kwargs)
        try:
            point = defaultRange
        except:
            point = 0
        self.fields['point'].initial = point

    def process(self):
        return self.cleaned_data['point']
