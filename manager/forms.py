import django
from django import forms
from django.db.models import Q
from django.utils import timezone
from .processupload import ProcessUpload
import manager.models as mmodels

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

    def __init__(self, user, view_type, object_id, analyte_id, *args, **kwargs):
        super(AddAnalytesForm, self).__init__(*args, **kwargs)
        if view_type == 'cs' :
            self.isCal = False
            cs = mmodels.CurveSet.objects.get(id=object_id)
            if not cs.canBeReadBy(user):
                raise 3
            cdata = cs.usedCurveData.all()
            curves_filter_qs = Q()
            for c in cdata:
                curves_filter_qs = curves_filter_qs | Q(id=c.curve.id, deleted=False)
            self.curves = mmodels.Curve.objects.filter(curves_filter_qs)
        elif view_type == "cf":
            cfile = mmodels.CurveFile.objects.get(id=object_id)
            if not cfile.canBeReadBy(user):
                raise 3
            self.curves = mmodels.Curve.objects.filter(curveFile=cfile)

        self.generateFields(analyte_id)

    def generateFields(self, analyte_id):
        analyte = None
        if analyte_id != 'new':
            try:
                analyte = mmodels.Analyte.objects.get(id=analyte_id)
                curves_filter_qs = Q()
                for c in self.curves:
                    curves_filter_qs = curves_filter_qs | Q(curve=c, analyte=analyte)
                aic = mmodels.AnalyteInCurve.objects.filter(curves_filter_qs)
            except:
                analyte = None
                aic = None
        else:
            analyte = None
            aic = None


        eaDefault = -1
        eaDefaultUnit = '0g'

        analytesFromDb = mmodels.Analyte.objects.all()
        existingAnalytes = [ (-1, 'Add new') ]
        if analytesFromDb:
            for an in analytesFromDb:
                existingAnalytes.append( (an.id, an.name) )

        if analyte is not None and aic:
            eaDefaultUnit = aic[0].concentrationUnits
            eaDefault = analyte.id

        self.fields['units'] = forms.ChoiceField(
            choices=mmodels.AnalyteInCurve.UNITSAVAILABLE,
            initial=eaDefaultUnit
        )

        self.fields['existingAnalyte'] = forms.ChoiceField(
            choices=existingAnalytes, 
            label="Analyte",
            initial=eaDefault
        )
        self.fields['existingAnalyte'].widget.attrs['class'] = 'testForNegative ifNegativeEnable@newAnalyte'
        self.fields['newAnalyte'] = forms.CharField(
            label="",
            max_length=128,
            required=False
        )
        self.fields['newAnalyte'].widget.attrs['class'] = 'newAnalyte'

        if aic:
            self.fields['newAnalyte'].initial = ""
            self.fields['newAnalyte'].widget.attrs['disabled'] = True

        for c in self.curves:
            if aic:
                ac = aic.filter(curve=c.id)
            else:
                ac = None
            if ac:
                self.fields["analyte_%d" % ac[0].id] = forms.FloatField(
                        label = c.name + ":\n" + c.comment ,
                        required = True,
                        initial = ac[0].concentration )
            else:
                self.fields["curve_%d" % c.id] = forms.FloatField(
                        label = c.name + ":\n" + c.comment ,
                        required = True )

    def clean(self):
        super().clean()
        if int(self.cleaned_data.get('existingAnalyte', -1)) == -1:
            if not self.cleaned_data.get('newAnalyte', '').strip():
                raise forms.ValidationError(
                    'New analyte cannot be empty string.'
                )


    def process(self, user):
        if int(self.cleaned_data.get('existingAnalyte', -1)) == -1:
            analyteName = self.cleaned_data.get('newAnalyte', '').strip()
            if not analyteName:
                #TODO: meaningful exception -- analyte cannot be empty
                raise 3 
            try:
                a = mmodels.Analyte.objects.get(name=analyteName)
            except mmodels.Analyte.DoesNotExist:
                a = mmodels.Analyte(name=analyteName)
                a.save()
        else:
            #try:
            a = mmodels.Analyte.objects.get(id=int(self.cleaned_data.get('existingAnalyte')))
            #except:
                #TODO: meaningfull exeption -- analyte id does not exists
                #raise 3

        units = self.cleaned_data['units']

        for name,val in self.cleaned_data.items():
            if "curve_" in name:
                curve_id = int(name[6:])
                if ( __debug__ ):
                    print("Updateing curve nr: %i with analyte %s, concentration: %s" % (curve_id, a.name, val))
                try:
                    c = mmodels.Curve.objects.get(id=curve_id)
                    f = mmodels.CurveFile.objects.get(id=c.curveFile.id)
                except (mmodels.Curve.DoesNotExist, mmodels.CurveFile.DoesNotExist):
                    continue

                if not f.canBeUpdatedBy(user):
                    raise 3

                aic = mmodels.AnalyteInCurve(
                    analyte=a, 
                    curve=c, 
                    concentration=float(val),
                    concentrationUnits=untis
                )
                aic.save()
            elif "analyte_" in name:
                analyte_in_id= int(name[8:])
                if ( __debug__ ):
                    print("Updateing analyte nr: %i, concentration: %s" % (analyte_in_id, val))
                try:
                    aic = mmodels.AnalyteInCurve.objects.get(id=analyte_in_id)
                except mmodels.AnalyteInCurve.DoesNotExist:
                    continue

                if not aic.canBeUpdatedBy(user):
                    raise 3

                aic.concentration = float(val)
                aic.concentrationUnits = units
                aic.analyte = a
                aic.save()
        return True


class SelectXForm(forms.Form):
    onXAxis = forms.ChoiceField(choices=mmodels.OnXAxis.AVAILABLE)

    def __init__(self, user, *args, **kwargs):
        self.user = user
        try:
            self.onx = mmodels.OnXAxis.objects.get(user=self.user)
        except mmodels.OnXAxis.DoesNotExist:
            self.onx = mmodels.OnXAxis(user=user)
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
        super(SelectCurvesForCurveSetForm, self).__init__(*args, **kwargs)
        from django.db.models import Prefetch
        self.fields['name'].maintype = 'name'
        self.fields['name'].mainid = 0

        files = mmodels.CurveFile.objects.filter(owner=user, deleted=False).only("id", "name", "filename")
        for f in files:
            fname = 'curveFile_{0}'.format(f.id)
            self.fields[fname] = forms.BooleanField(label=f,required=False)
            self.fields[fname].widget.attrs['class'] = 'parent'
            self.fields[fname].maintype = 'curvefile'
            self.fields[fname].cptype = 'parent'
            cf = mmodels.Curve.objects.filter(curveFile=f).values("id", "name")
            for c in cf:
                cname = "curveFile_{1}_curve_{0}".format(c['id'], f.id)
                self.fields[cname] = forms.BooleanField(label=c['name'], required=False)
                self.fields[cname].widget.attrs['class'] = 'child'
                self.fields[cname].maintype = 'curvefile'
                self.fields[cname].cptype = 'child'

        css = mmodels.CurveSet.objects.filter(owner=user, deleted=False).only("id", "name") 
        for cs in css:
            csname = 'curveSet_{0}'.format(cs.id)
            self.fields[csname] = forms.BooleanField(
                label=cs,
                required=False
            )
            self.fields[csname].maintype = 'curveset'
            self.fields[csname].widget.attrs['class'] = 'parent'
            self.fields[csname].cptype = 'parent'
            for c in cs.usedCurveData.only("id", "curve").prefetch_related(
                    Prefetch('curve', queryset=mmodels.Curve.objects.only('id','name'))
                ):
                cname = "curveSet_{1}_curveData_{0}".format(c.id, cs.id)
                self.fields[cname] = forms.BooleanField(label=c.curve, required=False)
                self.fields[cname].widget.attrs['class'] = 'child'
                self.fields[cname].maintype = 'curveset'
                self.fields[cname].cptype = 'child'

    def drawByHand(self, request):
        #TODO: Django template is order of magnitude too slow for this, so do it by hand ...
        token = django.middleware.csrf.get_token(request)
        ret = {}
        ret['start'] = """<form action="" method="post" id="SelectCurvesForCurveSetForm">
        <input type='hidden' name='csrfmiddlewaretoken' value='{token}' />
        <ul>""".format(token=token)
        ret['curveset'] = []
        ret['curvefile'] = []
        namefield = self.fields.pop('name')
        ret['start'] += """<li><input type="text" value="" name="name" /></li>"""
        prev_parent = ''
        for key,field in self.fields.items():
            if ( hasattr(self, 'cleaned_data' ) ):
                checked = self.cleaned_data.get(key, False)
            else:
                checked = False
            checkedtext = ''
            label = field.label
            if checked:
                checkedtext = ' checked'
            if field.cptype == 'parent':
                if prev_parent:
                    ret[prev_parent].append('</ul></li>')
                ret[field.maintype].append(
                    '<li class="menuItem parentLI invisible"><input class="parent" type="checkbox" name="{name}"{checkedText} /><label for="id_{name}">{label} </label><img src="https://upload.wikimedia.org/wikipedia/commons/f/f0/1DownRedArrow.png" class="EXPAND upsideup" /><ul>'.format(
                        name=key,
                        label=label,
                        checkedText=checkedtext
                    )
                )
                prev_parent = field.maintype
            else:
                ret[field.maintype].append(
                    '<li class="menuItem childClass invisible"><input class="child" type="checkbox" name="{name}"{checkedText} /><label for="id_{name}">{label}</label></li>'.format(
                        name=key,
                        label=label,
                        checkedText=checkedtext
                    )
                )
        if prev_parent:
            ret[prev_parent].append('</ul></li>')
        ret['end'] = '<li><input type="submit" name="Submit" value="submit" /></li></ul></form>'
        self.fields['name'] = namefield
        return ''.join([
            ret['start'], 
            '<li class="topClass">Files <img src="https://upload.wikimedia.org/wikipedia/commons/f/f0/1DownRedArrow.png" class="EXPAND upsideup" /><ul>',
            '\n'.join(ret['curvefile']),
            '</ul></li><li class="topClass">Curve sets <img src="https://upload.wikimedia.org/wikipedia/commons/f/f0/1DownRedArrow.png" class="EXPAND upsideup" /><ul>',
            '\n'.join(ret['curveset']), 
            '</ul></li>',
            ret['end']
        ])

    def process(self, user):
        final_curvedatas = []
        for name,val in self.cleaned_data.items():
            if ( '_' in name ):
                nameSplit = name.split('_')
                if ( len(nameSplit) > 2 ):
                    if "curve" == nameSplit[2]:
                        if ( val == True ) :
                            vid = int(nameSplit[3])
                            c = mmodels.Curve.objects.get(id=vid)
                            if not c.canBeReadBy(user):
                                raise 3
                            cd = mmodels.CurveData.objects.get(curve=c, processing=None)
                            final_curvedatas.append(cd)
                            
                    elif "curveData" == nameSplit[2]:
                        if ( val == True ):
                            vid = int(nameSplit[3])
                            cd = mmodels.CurveData.objects.get(id=vid)
                            if not cd.canBeReadBy(user):
                                raise 3
                            final_curvedatas.append(cd)
                else:
                    if "curveFile" == nameSplit[0]:
                        if ( val == True ) :
                            vid = int(nameSplit[1])
                            cf = mmodels.CurveFile.objects.get(id=vid)
                            if not cf.canBeReadBy(user):
                                raise 3
                            cc = mmodels.Curve.objects.filter(curveFile=cf, deleted=False)
                            for c in cc.all():
                                cd = mmodels.CurveData.objects.get(curve=c, processing=None)
                                final_curvedatas.append(cd)

                    elif "curveSet" == nameSplit[0]:
                        if ( val == True ) :
                            vid = int(nameSplit[1])
                            cs = mmodels.CurveSet.objects.get(id=vid)
                            if not cs.canBeReadBy(user):
                                raise 3
                            for cd in cs.usedCurveData.all():
                                final_curvedatas.append(cd)

        if len(final_curvedatas) == 0:
            return False
        final_curvedatas = list(set(final_curvedatas)) #only unique

        cs = mmodels.CurveSet(
                owner = user,
                name = self.cleaned_data['name'],
                date = timezone.now(),
                locked = False,
                deleted = False)
        cs.save()
        self.curvesetid = cs.id
        for cd in final_curvedatas:
            cs.usedCurveData.add(cd)
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
                if item.canBeUpdatedBy(user):
                    item.deleted = True
                    item.save()
                    return True
                else:
                    return False
