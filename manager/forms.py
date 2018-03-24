import django
from django import forms
from django.db import transaction
from django.db import DatabaseError
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
import manager
import manager.models as mmodels
from manager.exceptions import VoltPyNotAllowed


class CursorsForm(forms.Form):
    def __init__(self, *args, **kwargs):
        cursors_num = kwargs.pop('cursors_num', 1)
        super(CursorsForm, self).__init__(*args, **kwargs)
        for i in range(cursors_num):
            cname = ''.join(['val_cursor_', str(i)])
            self.fields[cname] = forms.CharField(max_length=24, label=str(i+1))
            self.fields[cname].widget.attrs['readonly'] = True


class GenericConfirmForm(forms.Form):
    confirm = forms.BooleanField(initial=False, label="Check to confirm")

    def confirmed(self):
        self.is_valid()
        if self.cleaned_data.get('confirm', False):
            return True
        else:
            return False


class EditName(forms.Form):
    def __init__(self, *args, **kwargs):
        self.model = kwargs.pop('model', None)
        label_name = kwargs.pop('label_name', '')
        super(EditName, self).__init__(*args, **kwargs)
        assert self.model is not None
        self.fields['e_name'] = forms.CharField(
            max_length=64, 
            initial=self.model.name,
            required=False,
            label=label_name
        )
        self.fields['e_id'] = forms.CharField(
            max_length=10,
            initial=self.model.id,
            required=True
        )
        self.fields['e_id'].widget = forms.HiddenInput()

    def process(self, user, request):
        if not self.model.canBeUpdatedBy(user):
            raise VoltPyNotAllowed
        try: 
            if self.model.id != int(self.cleaned_data['e_id']):
                raise VoltPyNotAllowed
        except:
            raise VoltPyNotAllowed
        self.model.name = self.cleaned_data['e_name']
        self.model.save()
        manager.helpers.functions.add_notification(request, 'Saved.', 0)


class EditAnalytesForm(forms.Form):
    # TODO: draw plot of file, provide fields for settings analytes
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
        existingAnalytes = [(-1, 'Add new')]
        if analytesFromDb:
            for an in analytesFromDb:
                existingAnalytes.append((an.id, an.name))

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
        self.fields['existingAnalyte'].widget.attrs['class'] = ' '.join([
            '_voltJS_testForNegative',
            '_voltJS_ifNegativeEnable@newAnalyte'
        ])
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
                val = self.cs.analytesConc.get(analyte.id, {}).get(cd.id, '')
            else:
                val = ''
            self.fields["curve_%d" % cd.id] = forms.FloatField(
                label=cd.curve.name + ":\n" + cd.curve.comment,
                required=True,
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
                # TODO: meaningful exception -- analyte cannot be empty
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
                # TODO: meaningfull exeption -- analyte id does not exists
                raise 3

        units = self.cleaned_data['units']

        conc = self.cs.analytesConc.get(a.id, {})

        for name, val in self.cleaned_data.items():
            if "curve_" in name:
                curve_id = int(name[6:])
                try:
                    self.cs.curvesData.get(id=curve_id)
                except ObjectDoesNotExist:
                    # TODO: something went really south ...
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
    curvesetid = -1

    def __init__(self, user,  *args, **kwargs):
        self.toClone = kwargs.pop('toClone', [])
        newName = ''
        try:
            if len(self.toClone) == 1:
                csToClone = mmodels.CurveSet.objects.get(id=self.toClone[0])
                if csToClone.canBeReadBy(user):
                    newName = csToClone.name + '_copy'
        except:
            newName = ''
            # self.toClone = -1
        super(SelectCurvesForCurveSetForm, self).__init__(*args, **kwargs)
        from django.db.models import Prefetch
        self.fields['name'] = forms.CharField(
            max_length=124, 
            required=True,
            initial=newName
        )
        self.fields['name'].maintype = 'name'
        self.fields['name'].mainid = 0

        files = mmodels.CurveFile.objects.filter(
            owner=user, 
            deleted=False
        ).only("id", "name", "fileName")
        csInFiles = []
        for f in files:
            fname = 'curveFile_{0}'.format(f.id)
            initial = False
            if f.curveSet.id in self.toClone:
                initial = True
            self.fields[fname] = forms.BooleanField(
                label=f,
                required=False,
                initial=initial
            )
            self.fields[fname].widget.attrs['class'] = 'parent'
            self.fields[fname].maintype = 'curvefile'
            self.fields[fname].cptype = 'parent'
            csInFiles.append(f.curveSet.id)
            for cd in f.curveSet.curvesData.all().only("id", "curve").prefetch_related(
                    Prefetch('curve', queryset=mmodels.Curve.objects.only('id', 'name'))
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
            initial = False
            if cs.id in self.toClone:
                initial = True
            self.fields[csname] = forms.BooleanField(
                label=cs,
                required=False,
                initial=initial
            )
            self.fields[csname].maintype = 'curveset'
            self.fields[csname].widget.attrs['class'] = 'parent'
            self.fields[csname].cptype = 'parent'
            for cd in cs.curvesData.only("id", "curve").prefetch_related(
                    Prefetch('curve', queryset=mmodels.Curve.objects.only('id', 'name'))
            ):
                cname = "curveSet_{1}_curveData_{0}".format(cd.id, cs.id)
                self.fields[cname] = forms.BooleanField(label=cd.curve, required=False)
                self.fields[cname].widget.attrs['class'] = 'child'
                self.fields[cname].maintype = 'curveset'
                self.fields[cname].cptype = 'child'

    def drawByHand(self, request):
        # TODO: Load curves dynamically after pressing extend 
        # TODO: Django template is order of magnitude too slow for this, so do it by hand ...
        token = django.middleware.csrf.get_token(request)
        ret = {}
        ret['start'] = """<form action="#" method="post" id="SelectCurvesForCurveSetForm">
        <input type='hidden' name='csrfmiddlewaretoken' value='{token}' />
        <ul>""".format(token=token)
        ret['curveset'] = []
        ret['curvefile'] = []
        namefield = self.fields.pop('name')
        ret['start'] += """
        <li class="main_list">Name: <input type="text" value="{0}" name="name"  autocomplete="off"/>
        </li>""".format(namefield.initial)
        prev_parent = ''
        for key, field in self.fields.items():
            if (hasattr(self, 'cleaned_data')):
                checked = self.cleaned_data.get(key, False)
            else:
                if self.fields.get(key).initial is True:
                    checked = True
                else:
                    checked = False
            checkedtext = ''
            label = field.label
            startingClass = "invisible"
            if checked:
                checkedtext = ' checked'
                startingClass = ""
            if field.cptype == 'parent':
                if prev_parent:
                    ret[prev_parent].append('</ul></li>')
                ret[field.maintype].append("""
<li class="_voltJS_toExpand cs_list {startingClass}">
    <input class="_voltJS_Disable" id="id_{name}" type="checkbox" name="{name}"{checkedText} />
    <label for="id_{name}">{label} </label>
    <button class="_voltJS_Expand"> Expand </button>
    <ul class="_voltJS_expandContainer _voltJS_disableContainer">
                    """.format(
                        name=key,
                        label=label,
                        checkedText=checkedtext,
                        startingClass=startingClass
                    )
                )
                prev_parent = field.maintype
            else:
                ret[field.maintype].append( """
<li class="_voltJS_toExpand curve_list {startingClass}">
    <input id="id_{name}" class="_voltJS_toDisable" type="checkbox" name="{name}"{checkedText} />
    <label for="id_{name}">{label}</label>
</li>
                    """.format(
                        name=key,
                        label=label,
                        checkedText=checkedtext,
                        startingClass=startingClass
                    )
                )
        if prev_parent:
            ret[prev_parent].append('</ul></li>')
        ret['end'] = '<li><input type="submit" name="Submit" value="submit" /></li></ul></form>'
        self.fields['name'] = namefield
        return ''.join([
            ret['start'], 
            '<li class="main_list"> Files <button class="_voltJS_Expand"> Expand </button><ul class="_voltJS_expandContainer">',
            '\n'.join(ret['curvefile']),
            '</ul></li>',
            '<li class="main_list"> CurveSets <button class="_voltJS_Expand"> Expand </button><ul class="_voltJS_expandContainer">',
            '\n'.join(ret['curveset']), 
            '</ul></li>',
            ret['end']
        ])


    @transaction.atomic 
    def process(self, user):
        sid = transaction.savepoint()

        selectedCS = {}
        selectedCF = {}
        for name, val in self.cleaned_data.items():
            if val is True:
                nameSplit = name.split('_')
                if len(nameSplit) == 2:
                    id1 = int(nameSplit[1])
                    if 'curveFile' == nameSplit[0]:
                        selectedCF[id1] = selectedCF.get(id1, {})
                        selectedCF[id1]['all'] = True
                    elif 'curveSet' == nameSplit[0]:
                        selectedCS[id1] = selectedCS.get(id1, {})
                        selectedCS[id1]['all'] = True
                elif len(nameSplit) == 4:
                    id1 = int(nameSplit[1])
                    id2 = int(nameSplit[3])
                    if 'curveFile' == nameSplit[0]:
                        selectedCF[id1] = selectedCF.get(id1, {})
                        selectedCF[id1][id2] = True
                    elif 'curveSet' == nameSplit[0]:
                        selectedCS[id1] = selectedCS.get(id1, {})
                        selectedCS[id1][id2] = True
        # Get CurveSet from CurveFile at the end to decrease number of operations
        for k, v in selectedCF.items():
            cf = mmodels.CurveFile.objects.get(id=k)
            selectedCS[cf.curveSet.id] = selectedCS.get(cf.curveSet.id, {})
            for vv in v.keys():
                selectedCS[cf.curveSet.id][vv] = True

        print('CSs:', selectedCS)

        if len(selectedCS) == 0:
            return False

        # Create new CurveSet:
        try:
            newcs = mmodels.CurveSet(
                owner=user,
                name=self.cleaned_data['name'],
                date=timezone.now(),
                locked=False,
                deleted=False
            )
            newcs.save()
            for csid, cdids in selectedCS.items():
                cs = mmodels.CurveSet.objects.get(id=csid)
                if not cs.canBeReadBy(user):
                    raise VoltPyNotAllowed()

                for a in cs.analytes.all():
                    if not newcs.analytes.filter(id=a.id).exists():
                        newcs.analytes.add(a)
                        newcs.analytesConcUnits[a.id] = cs.analytesConcUnits.get(a.id, '0g')
                if 'all' in cdids.keys():
                    for cd in cs.curvesData.all():
                        newcs.addCurve(
                            curveData=cd, 
                            curveConcDict=cs.getCurveConcDict(cd)
                        )
                else:
                    for cdid in cdids.keys():
                        cd = mmodels.CurveData.objects.get(id=cdid)
                        newcs.addCurve(
                            curveData=cd, 
                            curveConcDict=cs.getCurveConcDict(cd)
                        )
            newcs.save()
        except DatabaseError:
            transaction.savepoint_rollback(sid)
            raise
            return False
        transaction.savepoint_commit(sid)
        return newcs.id


class DeleteForm(forms.Form):
    areyousure = forms.BooleanField(label='Are you sure?', required=False)

    def __init__(self, item,  *args, **kwargs):
        super(DeleteForm, self).__init__(*args, **kwargs)
        self.fields['item_id'] = forms.CharField(
            widget=forms.HiddenInput(),
            initial=item.id
        )

    def process(self, user, item, deleteFrom=None):
        if self.cleaned_data['areyousure']:
            if self.cleaned_data['areyousure'] is True:
                form_item_id = int(self.cleaned_data['item_id'])
                if (form_item_id != int(item.id)):
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
