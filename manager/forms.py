import django
from django import forms
from django.db.models import Q
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
import manager.models as mmodels
from manager.processupload import ProcessUpload
import manager

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


class EditAnalytesForm(forms.Form):
    #TODO: draw plot of file, provide fields for settings analytes
    isCal = False

    def __init__(self, user, view_type, object_id, analyte_id, *args, **kwargs):
        super(EditAnalytesForm, self).__init__(*args, **kwargs)
        self.isCal = False
        self.cs = mmodels.CurveSet.objects.get(id=object_id)
        if not self.cs.canBeReadBy(user):
            raise VoltPyNotAllowed

        self.generateFields(analyte_id)
        self.original_id = analyte_id

    def generateFields(self, analyte_id):
        analyte = None
        if analyte_id != '-1':
            try:
                analyte = mmodels.Analyte.objects.get(id=analyte_id)
                conc = self.cs.analytesConc.get(analyte.id, {})
            except:
                analyte = None
                conc = {}
        else:
            analyte = None
            conc = {}


        eaDefault = -1
        eaDefaultUnit = '0g'

        analytesFromDb = mmodels.Analyte.objects.all()
        existingAnalytes = [ (-1, 'Add new') ]
        if analytesFromDb:
            for an in analytesFromDb:
                existingAnalytes.append( (an.id, an.name) )

        if analyte is not None and conc:
            eaDefaultUnit = self.cs.analytesConcUnits.get(analyte.id, eaDefaultUnit)
            eaDefault = analyte.id

        self.fields['units'] = forms.ChoiceField(
            choices=mmodels.CurveSet.CONC_UNITS,
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

        if conc is not None:
            self.fields['newAnalyte'].initial = ""
            self.fields['newAnalyte'].widget.attrs['disabled'] = True

        for cd in self.cs.curvesData.all():
            if analyte is not None:
                val = self.cs.analytesConc.get(analyte.id,{}).get(cd.id,'')
            else:
                val = ''
            self.fields["curve_%d" % cd.id] = forms.FloatField(
                label = cd.curve.name + ":\n" + cd.curve.comment ,
                required = True,
                initial=val
            )

    def clean(self):
        super().clean()
        if int(self.cleaned_data.get('existingAnalyte', -1)) == -1:
            if not self.cleaned_data.get('newAnalyte', '').strip():
                raise forms.ValidationError(
                    'New analyte cannot be empty string.'
                )


    def process(self, user):
        a = None
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
            try:
                a = mmodels.Analyte.objects.get(id=int(self.cleaned_data.get('existingAnalyte')))
            except:
                #TODO: meaningfull exeption -- analyte id does not exists
                raise 3

        units = self.cleaned_data['units']

        conc = self.cs.analytesConc.get(a.id, {})

        for name,val in self.cleaned_data.items():
            if "curve_" in name:
                curve_id = int(name[6:])
                if ( __debug__ ):
                    print("Updateing curve nr: %i with analyte %s, concentration: %s" % (curve_id, a.name, val))
                try:
                    self.cs.curvesData.get(id=curve_id)
                except ObjectDoesNotExist:
                    #TODO: something went really south ...
                    raise 3

                if not self.cs.canBeUpdatedBy(user):
                    raise 3
                
                conc[curve_id] = float(val)

        if not self.cs.analytes.filter(id=a.id).exists():
            self.cs.analytes.add(a)

        if manager.helpers.functions.isNumber(self.original_id) and a.id != self.original_id:
            self.cs.analytesConc.pop(self.original_id, None)
            self.cs.analytesConcUnits.pop(self.original_id, None)
            try:
                a_org = mmodels.Analyte.objects.get(id=self.original_id)
                self.cs.analytes.remove(a_org)
            except ObjectDoesNotExist:
                pass
        self.cs.analytesConc[a.id] = conc
        self.cs.analytesConcUnits[a.id] = units
        self.cs.analytes.add(a)
        self.cs.save()
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

        files = mmodels.CurveFile.objects.filter(owner=user, deleted=False).only("id", "name", "fileName")
        csInFiles = []
        for f in files:
            fname = 'curveFile_{0}'.format(f.id)
            self.fields[fname] = forms.BooleanField(label=f,required=False)
            self.fields[fname].widget.attrs['class'] = 'parent'
            self.fields[fname].maintype = 'curvefile'
            self.fields[fname].cptype = 'parent'
            csInFiles.append(f.curveSet.id)
            for cd in f.curveSet.curvesData.all().only("id", "curve").prefetch_related(
                    Prefetch('curve', queryset=mmodels.Curve.objects.only('id','name'))
                ):
                cname = "curveFile_{1}_curveData_{0}".format(cd.id, f.id)
                self.fields[cname] = forms.BooleanField(label=cd.curve, required=False)
                self.fields[cname].widget.attrs['class'] = 'child'
                self.fields[cname].maintype = 'curvefile'
                self.fields[cname].cptype = 'child'

        css = mmodels.CurveSet.objects.filter(owner=user, deleted=False).only("id", "name") 
        for cs in css:
            if cs.id in csInFiles:
                continue
            csname = 'curveSet_{0}'.format(cs.id)
            self.fields[csname] = forms.BooleanField(
                label=cs,
                required=False
            )
            self.fields[csname].maintype = 'curveset'
            self.fields[csname].widget.attrs['class'] = 'parent'
            self.fields[csname].cptype = 'parent'
            for cd in cs.curvesData.only("id", "curve").prefetch_related(
                    Prefetch('curve', queryset=mmodels.Curve.objects.only('id','name'))
                ):
                cname = "curveSet_{1}_curveData_{0}".format(cd.id, cs.id)
                self.fields[cname] = forms.BooleanField(label=cd.curve, required=False)
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
        analytesUnits = {}
        for name,val in self.cleaned_data.items():
            if ( val == True ):
                if ( '_' in name ):
                    nameSplit = name.split('_')
                    if "curveFile" == nameSplit[0]:
                        vid = int(nameSplit[1])
                        cf = mmodels.CurveFile.objects.get(id=vid)
                        for a in cf.curveSet.analytes.all():
                            analytesConcUnits[a.id] = cf.curveSet.analytesConcUnits[a.id]
                            analytesConc[a.id] = {}

                    elif "curveSet" == nameSplit[0]:
                        vid = int(nameSplit[1])
                        cs = mmodels.CurveSet.objects.get(id=vid).only('analytes')
                        for a in cs.analytes.all():
                            analytesConcUnits[a.id] = cs.analytesConcUnits[a.id]
                            analytesConc[a.id] = {}

        final_curvedatas = []
        analytesConc = {}
        for name,val in self.cleaned_data.items():
            if ( val == True ):
                if ( '_' in name ):
                    nameSplit = name.split('_')
                    if len(nameSplit) > 2:
                        if "curveFile" == nameSplit[0]:
                            vid = int(nameSplit[1])
                            cf = mmodels.CurveFile.objects.get(id=vid)
                            if "curveData" == nameSplit[2]:
                                if ( val == True ) :
                                    vid = int(nameSplit[3])
                                    cd = mmodels.CurveData.objects.get(id=vid).only('id','owner')
                                    if not cd.canBeReadBy(user):
                                        raise 3
                                    final_curvedatas.append(cd)
                                    for aid,v in analytesAndUnits.items():
                                        analytesConc[aid][cd.id] = cf.curveSet.analytesConc.get(aid,{}).get(cd.id,0)
                        elif "curveSet" == nameSplit[0]:
                            if "curveData" == nameSplit[2]:
                                    vid = int(nameSplit[3])
                                    cd = mmodels.CurveData.objects.get(id=vid).only('id','owner')
                                    if not cd.canBeReadBy(user):
                                        raise 3
                                    final_curvedatas.append(cd)
                                    for aid,v in analytesAndUnits.items():
                                        analytesConc[aid][cd.id] = cs.analytesConc.get(aid,{}).get(cd.id,0)
                    else:
                        if "curveFile" == nameSplit[0]:
                            if ( val == True ) :
                                vid = int(nameSplit[1])
                                cf = mmodels.CurveFile.objects.get(id=vid)
                                if not cf.canBeReadBy(user):
                                    raise 3
                                cs = cf.curveSet;
                                for cd in cs.curvesData.all():
                                    final_curvedatas.append(cd)
                                    for aid,v in analytesConc.items():
                                        analytesConc[aid][cd.id] = cs.analytesConc.get(aid,{}).get(cd.id,0)

                        elif "curveSet" == nameSplit[0]:
                            if ( val == True ) :
                                vid = int(nameSplit[1])
                                cs = mmodels.CurveSet.objects.get(id=vid)
                                if not cs.canBeReadBy(user):
                                    raise 3
                                for cd in cs.curvesData.all():
                                    final_curvedatas.append(cd)
                                    for aid,v in analytesConc.items():
                                        analytesConc[aid][cd.id] = cs.analytesConc.get(aid,{}).get(cd.id,0)

        if len(final_curvedatas) == 0:
            return False
        final_curvedatas = list(set(final_curvedatas)) #only unique

        cs = mmodels.CurveSet(
            owner = user,
            name = self.cleaned_data['name'],
            date = timezone.now(),
            locked = False,
            deleted = False
        )
        cs.analytesConc = analytesConc
        cs.analytesConcUnits = analytesConcUnits
        for aid,v in analytesConcUnits.items():
            cs.analyets.add(mmodels.Analytes.objects.get(id=aid))
        cs.save()
        self.curvesetid = cs.id
        for cd in final_curvedatas:
            cs.curvesData.add(cd)
        cs.save()
        return True


class DeleteForm(forms.Form):
    areyousure = forms.BooleanField(label = 'Are you sure?', required=False)

    def __init__(self, item,  *args, **kwargs):
        super(DeleteForm, self).__init__(*args, **kwargs)
        self.fields['item_id'] = forms.CharField(
            widget=forms.HiddenInput(),
            initial=item.id
        )

    def process(self, user, item, deleteFrom=None):
        if ( self.cleaned_data['areyousure'] ):
            if ( self.cleaned_data['areyousure'] == True ):
                form_item_id = int(self.cleaned_data['item_id'])
                if ( form_item_id != int(item.id) ):
                    return False
                if item.canBeUpdatedBy(user):
                    if deleteFrom is None \
                    or deleteFrom.__class__.__name__ != 'CurveSet':
                        item.deleted = True
                        item.save()
                        return True
                    else:
                        deleteFrom.curvesData.remove(item)
                        deleteFrom.save()
                        return True
                else:
                    return False
