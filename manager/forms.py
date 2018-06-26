import django
from django import forms
from django.db import transaction
from django.db import DatabaseError
from django.utils import timezone
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.utils.safestring import mark_safe
import django.core.validators as validators
from django.contrib.auth.password_validation import validate_password
import manager
import manager.models as mmodels
from manager.exceptions import VoltPyNotAllowed
from manager.exceptions import VoltPyDoesNotExists


class SignInForm(UserCreationForm):
    email = forms.EmailField(max_length=254, help_text='Required. Inform a valid email address.')

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2', )


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


class SettingsForm(forms.Form):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        if user is None:
            raise VoltPyNotAllowed('Operation not allowed')
        super(SettingsForm, self).__init__(*args, **kwargs)


class ChangePassForm(forms.Form):
    redirect = False
    old_password = forms.CharField(
        label="Old password",
        max_length=128,
        initial='',
        widget=forms.PasswordInput
    )
    new_password = forms.CharField(
        label="New password",
        max_length=128,
        initial='',
        widget=forms.PasswordInput,
        help_text="""
<small>
<ul>
<li>Your password can't be too similar to your other personal information.</li>
<li>Your password must contain at least 8 characters.</li>
<li>Your password can't be a commonly used password.</li>
<li>Your password can't be entirely numeric.</li>
</ul>
</small>
        """
    )
    new_password2 = forms.CharField(
        label="Retype new password",
        max_length=128,
        initial='',
        widget=forms.PasswordInput
    )

    def clean(self):
        super().clean()
        validate_password(self.cleaned_data['new_password'], manager.helpers.functions.get_user())

    def process(self, user, request):
        if user.check_password(self.cleaned_data['old_password']):
            if self.cleaned_data['new_password'] == self.cleaned_data['new_password2']:
                user.set_password(self.cleaned_data['new_password'])
                user.save()
                manager.helpers.functions.add_notification(request, 'Password changed')
                self.redirect = True
            else:
                manager.helpers.functions.add_notification(request, 'Passwords do not match')
        else:
            manager.helpers.functions.add_notification(request, 'Incorrect password')


class ChangeEmailForm(forms.Form):
    redirect = False
    password = forms.CharField(
        label="Password",
        max_length=128,
        initial='',
        widget=forms.PasswordInput
    )
    new_email = forms.CharField(
        label="New email",
        max_length=255,
        initial='',
        validators=[validators.EmailValidator]
    )
    new_email2 = forms.CharField(
        label="Retype email",
        max_length=255,
        initial='',
        validators=[validators.EmailValidator]
    )

    def process(self, user, request):
        if user.check_password(self.cleaned_data['password']):
            if self.cleaned_data['new_email'] == self.cleaned_data['new_email2']:
                # TODO: send verification email
                user.email = self.cleaned_data['new_email']
                user.save()
                manager.helpers.functions.add_notification(request, 'Email changed')
                self.redirect = True
            else:
                manager.helpers.functions.add_notification(request, 'Emails do not match')
        else:
            manager.helpers.functions.add_notification(request, 'Incorrect password')


class EditName(forms.Form):
    def __init__(self, *args, **kwargs):
        self.model = kwargs.pop('model', None)
        label_name = kwargs.pop('label_name', '')
        super(EditName, self).__init__(*args, **kwargs)
        assert self.model is not None
        self.fields['e_name'] = forms.CharField(
            max_length=128,
            initial=self.model.name,
            required=False,
            label=label_name,
            widget=forms.TextInput(attrs={'size': 30})
        )
        self.fields['e_id'] = forms.CharField(
            max_length=10,
            initial=self.model.id,
            required=True
        )
        self.fields['e_id'].widget = forms.HiddenInput()

    def process(self, user, request):
        try:
            if self.model.id != int(self.cleaned_data['e_id']):
                raise VoltPyNotAllowed
        except:
            raise VoltPyNotAllowed
        self.model.name = self.cleaned_data['e_name']
        self.model.save()
        manager.helpers.functions.add_notification(request, 'Saved.', 0)


class EditCurvesForm(forms.Form):
    def __init__(self, user, dataset, *args, **kwargs):
        super(EditCurvesForm, self).__init__(*args, **kwargs)
        self.cs = dataset
        self.generateFields()

    def generateFields(self):
        for cd in self.cs.curves_data.all():
            self.fields['curve_%d_name' % cd.id] = forms.CharField(
                label='Name',
                required=True,
                initial=cd.curve.name,
                max_length=255,
            )
            self.fields['curve_%d_name' % cd.id].widget.attrs['class'] = ' '.join([
                '_voltJS_plotHighlightInput',
                '_voltJS_highlightCurve@%d' % cd.id,
            ])
            self.fields['curve_%d_comment' % cd.id] = forms.CharField(
                label='Comment',
                required=False,
                initial=cd.curve.comment,
                max_length=255,
            )
            self.fields['curve_%d_comment' % cd.id].widget.attrs['class'] = ' '.join([
                '_voltJS_plotHighlightInput',
                '_voltJS_highlightCurve@%d' % cd.id,
            ])

    def process(self, user):
        # TODO: Perms to what are required (?)
        if not user.has_perm('rw', self.cs):
            raise VoltPyNotAllowed('Not allowed to change the dataset.')
        for cd in self.cs.curves_data.all():
            name = self.cleaned_data.get('curve_%d_name' % cd.id, None)
            comment = self.cleaned_data.get('curve_%d_comment' % cd.id, None)
            if name is None or comment is None:
                raise VoltPyNotAllowed('Incomplete form, please try again.')
            cd.curve.name = name
            cd.curve.comment = comment
            cd.curve.save()
        return True


class EditAnalytesForm(forms.Form):
    isCal = False

    def __init__(self, user, dataset, analyte_id, *args, **kwargs):
        super(EditAnalytesForm, self).__init__(*args, **kwargs)
        self.isCal = False
        self.cs = dataset
        self.generateFields(user, analyte_id)
        self.original_id = analyte_id

    def generateFields(self, user, analyte_id):
        analyte = None
        if analyte_id != '-1':
            try:
                analyte = mmodels.Analyte.get(id=analyte_id)
                conc = self.cs.analytes_conc.get(analyte.id, {})
            except:
                analyte = None
                conc = {}
        else:
            analyte = None
            conc = {}

        eaDefault = -1
        eaDefaultUnit = '0g'

        analytesFromDb = mmodels.Analyte.objects.filter(owner=user)
        existingAnalytes = [(-1, 'Add new')]
        if analytesFromDb:
            for an in analytesFromDb:
                existingAnalytes.append((an.id, an.name))

        if analyte is not None and conc:
            eaDefaultUnit = self.cs.analytes_conc_unit.get(analyte.id, eaDefaultUnit)
            eaDefault = analyte.id

        self.fields['units'] = forms.ChoiceField(
            choices=mmodels.Dataset.CONC_UNITS,
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
            required=False,
            widget=forms.TextInput(attrs={
                'placeholder': 'New analyte name',
                'class': 'newAnalyte'
            })
        )

        if conc is not None:
            self.fields['newAnalyte'].initial = ""
            self.fields['newAnalyte'].widget.attrs['disabled'] = True

        for cd in self.cs.curves_data.all():
            if analyte is not None:
                val = self.cs.analytes_conc.get(analyte.id, {}).get(cd.id, '')
            else:
                val = ''
            self.fields['curve_%d' % cd.id] = forms.FloatField(
                label=mark_safe(cd.curve.name + "<br /><small>" + cd.curve.comment + '</small>'),
                required=True,
                initial=val
            )
            self.fields['curve_%d' % cd.id].widget.attrs['class'] = ' '.join([
                '_voltJS_plotHighlightInput',
                '_voltJS_highlightCurve@%d' % cd.id,
            ])

    def clean(self):
        super().clean()
        try:
            an_id = int(self.cleaned_data.get('existingAnalyte', -1))
            self.cleaned_data['existingAnalyte'] = an_id
        except ValueError:
            raise forms.ValidationError(
                'Wrong value for selected analyte.'
            )
        if an_id == -1:
            if not self.cleaned_data.get('newAnalyte', '').strip():
                raise forms.ValidationError(
                    'New analyte cannot be empty string.'
                )
            else:
                self.cleaned_data['newAnalyte'] = self.cleaned_data.get('newAnalyte', '').strip()
        else:
            if not mmodels.Analyte.objects.filter(id=an_id).exists():
                raise forms.ValidationError(
                    'Could not identify selected analyte.'
                )

        return self.cleaned_data

    def process(self, user):
        if not user.has_perm('rw', self.cs):
            raise VoltPyNotAllowed('Operation not allowed.')

        a = None
        if int(self.cleaned_data.get('existingAnalyte', -1)) == -1:
            analyteName = self.cleaned_data['newAnalyte']
            try:
                a = mmodels.Analyte.objects.get(name=analyteName)
            except mmodels.Analyte.DoesNotExist:
                a = mmodels.Analyte(name=analyteName, owner=user)
                a.save()
        else:
            a = mmodels.Analyte.objects.get(id=self.cleaned_data['existingAnalyte'])

        units = self.cleaned_data['units']

        conc = self.cs.analytes_conc.get(a.id, {})

        for name, val in self.cleaned_data.items():
            if "curve_" in name:
                curve_id = int(name[6:])
                try:
                    self.cs.curves_data.get(id=curve_id)
                except ObjectDoesNotExist:
                    raise VoltPyDoesNotExists('Curve id %d does not exists.' % curve_id)

                conc[curve_id] = float(val)

        if not self.cs.analytes.filter(id=a.id).exists():
            self.cs.analytes.add(a)

        if all([
            manager.helpers.functions.is_number(self.original_id),
            a.id != self.original_id
        ]):
            self.cs.analytes_conc.pop(self.original_id, None)
            self.cs.analytes_conc_unit.pop(self.original_id, None)
            try:
                a_org = mmodels.Analyte.objects.get(id=self.original_id)
                self.cs.analytes.remove(a_org)
            except ObjectDoesNotExist:
                pass
        self.cs.analytes_conc[a.id] = conc
        self.cs.analytes_conc_unit[a.id] = units
        self.cs.analytes.add(a)
        self.cs.save()
        return True

"""
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
"""


class SelectCurvesForDatasetForm(forms.Form):
    dataset_id = -1

    def __init__(self, user,  *args, **kwargs):
        self.toCloneCS = kwargs.pop('toCloneCS', [])
        self.toCloneCF = kwargs.pop('toCloneCF', [])
        if len(self.toCloneCF) > 0 and len(self.toCloneCS) > 0:
            raise VoltPyNotAllowed('Can only clone one type of data.')
        newName = ''
        try:
            if len(self.toCloneCS) == 1:
                csToClone = mmodels.Dataset.get(id=self.toCloneCS[0])
                newName = csToClone.name + '_copy'
            if len(self.toCloneCF) == 1:
                csToClone = mmodels.File.get(id=self.toCloneCF[0])
                newName = csToClone.name + '_copy'
        except:
            newName = ''
            # self.toClone = -1
        super(SelectCurvesForDatasetForm, self).__init__(*args, **kwargs)
        from django.db.models import Prefetch
        self.fields['name'] = forms.CharField(
            max_length=124,
            required=True,
            initial=newName
        )
        self.fields['name'].maintype = 'name'
        self.fields['name'].mainid = 0

        files = mmodels.File.all()
        csInFiles = []
        for f in files:
            fname = 'File_{0}'.format(f.id)
            initial = False
            if f.id in self.toCloneCF:
                initial = True
            self.fields[fname] = forms.BooleanField(
                label=f,
                required=False,
                initial=initial
            )
            self.fields[fname].widget.attrs['class'] = 'parent'
            self.fields[fname].maintype = 'file'
            self.fields[fname].cptype = 'parent'
            csInFiles.append(f.id)
            for cd in f.curves_data.all().only("id", "curve").prefetch_related(
                    Prefetch('curve', queryset=mmodels.Curve.objects.only('id', 'name'))
            ):
                cname = "File_{1}_curveData_{0}".format(cd.id, f.id)
                self.fields[cname] = forms.BooleanField(label=cd.curve, required=False)
                self.fields[cname].widget.attrs['class'] = 'child'
                self.fields[cname].maintype = 'file'
                self.fields[cname].cptype = 'child'

        css = mmodels.Dataset.all().only("id", "name") 
        for cs in css:
            if cs.id in csInFiles:
                continue
            csname = 'dataset_{0}'.format(cs.id)
            initial = False
            if cs.id in self.toCloneCS:
                initial = True
            self.fields[csname] = forms.BooleanField(
                label=cs,
                required=False,
                initial=initial
            )
            self.fields[csname].maintype = 'dataset'
            self.fields[csname].widget.attrs['class'] = 'parent'
            self.fields[csname].cptype = 'parent'
            for cd in cs.curves_data.only("id", "curve").prefetch_related(
                    Prefetch('curve', queryset=mmodels.Curve.objects.only('id', 'name'))
            ):
                cname = "dataset_{1}_curveData_{0}".format(cd.id, cs.id)
                self.fields[cname] = forms.BooleanField(label=cd.curve, required=False)
                self.fields[cname].widget.attrs['class'] = 'child'
                self.fields[cname].maintype = 'dataset'
                self.fields[cname].cptype = 'child'

    def drawByHand(self, request) -> str:
        # TODO: Load curves dynamically after pressing extend 
        # TODO: Django template is order of magnitude too slow for this, so do it by hand ...
        token = django.middleware.csrf.get_token(request)
        ret = {}
        ret['start'] = """<form action="./" method="POST" id="SelectCurvesForDatasetForm">
        <input type='hidden' name='csrfmiddlewaretoken' value='{token}' />
        <ul>""".format(token=token)
        ret['dataset'] = []
        ret['file'] = []
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
    <button class="_voltJS_Expand"> Show curves </button>
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
                ret[field.maintype].append("""
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
        ret['end'] = '<hr /><li><input type="submit" name="Submit" value="Create New Dataset" /></li></ul></form>'
        self.fields['name'] = namefield
        return ''.join([
            ret['start'], 
            '<hr /><li class="main_list"><button class="_voltJS_Expand"> Toggle files view </button><ul class="_voltJS_expandContainer">',
            '\n'.join(ret['file']),
            '</ul></li><hr />',
            '<li class="main_list"><button class="_voltJS_Expand"> Toggle datasets view </button><ul class="_voltJS_expandContainer">',
            '\n'.join(ret['dataset']), 
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
                    if 'File' == nameSplit[0]:
                        selectedCF[id1] = selectedCF.get(id1, {})
                        selectedCF[id1]['all'] = True
                    elif 'dataset' == nameSplit[0]:
                        selectedCS[id1] = selectedCS.get(id1, {})
                        selectedCS[id1]['all'] = True
                elif len(nameSplit) == 4:
                    id1 = int(nameSplit[1])
                    id2 = int(nameSplit[3])
                    if 'File' == nameSplit[0]:
                        selectedCF[id1] = selectedCF.get(id1, {})
                        selectedCF[id1][id2] = True
                    elif 'dataset' == nameSplit[0]:
                        selectedCS[id1] = selectedCS.get(id1, {})
                        selectedCS[id1][id2] = True

        if len(selectedCS) == 0 and len(selectedCF) == 0:
            return False

        # Create new Dataset:
        try:
            newcs = mmodels.Dataset(
                owner=user,
                name=self.cleaned_data['name'],
                date=timezone.now(),
                deleted=False
            )
            newcs.save()

            def fun(selected_data, cf_or_cs):
                for csid, cdids in selected_data.items():
                    if cf_or_cs == 'dataset':
                        cs = mmodels.Dataset.get(id=csid)
                    else:
                        cs = mmodels.File.get(id=csid)

                    for a in cs.analytes.all():
                        if not newcs.analytes.filter(id=a.id).exists():
                            newcs.analytes.add(a)
                            newcs.analytes_conc_unit[a.id] = cs.analytes_conc_unit.get(a.id, '0g')
                    if 'all' in cdids.keys():
                        for cd in cs.curves_data.all():
                            newcs.addCurve(
                                cd=cd,
                                conc_dict=cs.getCurveConcDict(cd)
                            )
                    else:
                        for cdid in cdids.keys():
                            cd = mmodels.CurveData.get(id=cdid)
                            newcs.addCurve(
                                cd=cd,
                                conc_dict=cs.getCurveConcDict(cd)
                            )
                newcs.save()
            fun(selectedCF, 'file')
            fun(selectedCS, 'dataset')
        except DatabaseError:
            transaction.savepoint_rollback(sid)
            raise
            return False
        transaction.savepoint_commit(sid)
        return newcs.id


class DeleteForm(forms.Form):
    areyousure = forms.BooleanField(label='Are you sure?', required=False)

    def __init__(self, item, *args, **kwargs):
        super(DeleteForm, self).__init__(*args, **kwargs)
        self.fields['item_id'] = forms.CharField(
            widget=forms.HiddenInput(),
            initial=item.id
        )

    def process(self, item, delete_fun=None):
        if self.cleaned_data['areyousure']:
            if self.cleaned_data['areyousure'] is True:
                form_item_id = int(self.cleaned_data['item_id'])
                if (form_item_id != int(item.id)):
                    return False
                if delete_fun is None:
                    item.delete()
                    return True
                else:
                    delete_fun(item)
                    return True
