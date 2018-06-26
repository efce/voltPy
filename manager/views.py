import json
from guardian.shortcuts import remove_perm
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User, Group
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseRedirect
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.template import loader
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.encoding import force_text
from django.utils.http import urlsafe_base64_encode
from django.utils.http import urlsafe_base64_decode
from django.contrib.sites.models import Site
from manager.forms import SignInForm
from manager.tokens import account_activation_token
import manager.models as mmodels
import manager.forms as mforms
import manager.uploads.uploadmanager as umanager
from manager.operations import methodmanager as mmm
from manager.exceptions import VoltPyNotAllowed, VoltPyDoesNotExists
from manager.helpers.functions import add_notification
from manager.helpers.functions import delete_helper
from manager.helpers.functions import form_helper
from manager.helpers.functions import generate_plot
from manager.helpers.functions import voltpy_render
from manager.helpers.functions import voltpy_serve_csv
from manager.helpers.functions import is_number
from manager.helpers.functions import get_redirect_class
from manager.helpers.functions import get_shared_object
from manager.helpers.functions import generate_share_link
from manager.helpers.functions import paginate
from manager.helpers.decorators import with_user
from manager.helpers.decorators import redirect_on_voltpyexceptions


@redirect_on_voltpyexceptions
def register(request):
    if request.method == 'POST':
        form = SignInForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()
            current_site = get_current_site(request)
            subject = 'Activate Your VoltPy Account'
            message = loader.render_to_string('registration/account_activation_email.html', {
                'user': user,
                'domain': Site.objects.get_current(),
                'uid': urlsafe_base64_encode(force_bytes(user.pk)).decode(),
                'token': account_activation_token.make_token(user),
            })
            user.email_user(subject, message)
            return redirect('account_activation_sent')
    else:
        form = SignInForm()
    return render(request, 'registration/signin.html', {'form': form})


@redirect_on_voltpyexceptions
def activate(request, uidb64, token):
    # TODO: move logic somewhere else:
    try:
        uid = force_text(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.profile.email_confirmed = True
        user.save()
        group = Group.objects.get(name='registered_users')
        group.user_set.add(user)
        group.save()
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        return redirect('index')
    else:
        return render(request, 'registration/account_activation_invalid.html')


@redirect_on_voltpyexceptions
def account_activation_sent(request):
    context = {'user': None}
    return voltpy_render(
        request=request,
        template_name='registration/account_activation_sent.html',
        context=context
    )


@redirect_on_voltpyexceptions
def acceptCookies(request):
    from django.http import HttpResponse
    request.session['accepted_cookies'] = True
    return HttpResponse('')


@redirect_on_voltpyexceptions
def termsOfService(request):
    context = {}
    if request.user:
        context['user'] = request.user
    return voltpy_render(
        request=request,
        template_name="manager/tos.html",
        context=context,
    )


@redirect_on_voltpyexceptions
def privacyPolicy(request):
    context = {}
    if request.user:
        context['user'] = request.user
    return voltpy_render(
        request=request,
        template_name="manager/privacy_policy.html",
        context=context,
    )


@redirect_on_voltpyexceptions
def index(request):
    context = {'request': request}
    return voltpy_render(
        request=request,
        template_name='manager/index.html',
        context=context
    )


@redirect_on_voltpyexceptions
@with_user
def sharing(request, user):
    shared = mmodels.SharedLink.all()
    context = {
        'user': user,
        'shared': shared,
    }
    return voltpy_render(
        request=request,
        template_name='manager/sharing.html',
        context=context
    )


@redirect_on_voltpyexceptions
@with_user
def changePassword(request, user):
    if (request.method == 'POST'):
        if request.POST.get('_voltJS_backButton', False):
            return HttpResponseRedirect(reverse('settings'))

    form_ret = form_helper(
        user=user,
        request=request,
        formClass=mforms.ChangePassForm,
        submitName='changePass',
        submitText='Submit',
        formTemplate='manager/form.html',
        #formExtraData=None,
    )
    if form_ret['instance'].redirect:
        return HttpResponseRedirect(reverse('settings'))
    return voltpy_render(
        request=request,
        template_name="manager/display.html",
        context={
            'user': user,
            'display': form_ret['html'],
            'window_title': 'Change email',
            'fieldset_title': 'Change email',
            'extra_style': '#id_new_password {margin-top: 20px;}',
        }
    )


@redirect_on_voltpyexceptions
@with_user
def changeEmail(request, user):
    if (request.method == 'POST'):
        if request.POST.get('_voltJS_backButton', False):
            return HttpResponseRedirect(reverse('settings'))

    form_ret = form_helper(
        user=user,
        request=request,
        formClass=mforms.ChangeEmailForm,
        submitName='changeMail',
        submitText='Submit',
        formTemplate='manager/form.html',
    )
    if form_ret['instance'].redirect:
        return HttpResponseRedirect(reverse('settings'))
    return voltpy_render(
        request=request,
        template_name="manager/display.html",
        context={
            'user': user,
            'display': form_ret['html'],
            'window_title': 'Change email',
            'fieldset_title': 'Change email',
        }
    )


@redirect_on_voltpyexceptions
def confirmNewEmail(request, uid, token):
    user = User.objects.filter(id=uid)
    if not user.exists():
        raise VoltPyNotAllowed('Unknown code or already used')
    user = user[0]
    if user.profile.new_email_confirmation_hash == token:
        user.email = user.profile.new_email
        user.save()
        user.profile.new_email = None
        user.profile.new_email_confirmation_hash = None
        user.profile.save()
        add_notification(request, 'Email changed')
        return HttpResponseRedirect('index')
    else:
        raise VoltPyNotAllowed('Unknown code or already used')


@redirect_on_voltpyexceptions
@with_user
def settings(request, user):
    if request.method == 'POST':
        if request.POST.get('apply_settings', False):
            form = mforms.SettingsForm(request, user=user)
            if form.is_valid():
                add_notification(request, 'Changes saved')
            else:
                add_notification(request, 'Settings form error')
        else:
            form = mforms.SettingsForm(user=user)
    else:
        form = mforms.SettingsForm(user=user)
    context = {
        'user': user,
        'form': form,
    }
    return voltpy_render(
        request=request,
        template_name='manager/settings.html',
        context=context
    )


@redirect_on_voltpyexceptions
@with_user
def export(request, user, obj_type, obj_id):
    allowedTypes = ('fileset', 'file', 'dataset', 'analysis')
    assert obj_type in allowedTypes
    try:
        csv_file = ''
        filename = 'export_%s.csv'
        if obj_type == 'fileset':
            fs = mmodels.Fileset.get(id=int(obj_id), deleted=False)
            csv_file = fs.export()
            filename = filename % fs.name
        elif obj_type == 'file':
            cf = mmodels.File.get(id=int(obj_id))
            csv_file = cf.export()
            filename = filename % cf.name
        elif obj_type == 'dataset':
            ds = mmodels.Dataset.get(id=int(obj_id))
            csv_file = ds.export()
            filename = filename % ds.name
        elif obj_type == 'analysis':
            mm = mmm.MethodManager(user=user, analysis_id=obj_id)
            csv_file, modelName = mm.exportFile()
            filename = 'analysis_%s.csv' % (modelName if modelName else ('id_%s' % obj_id))
    except ObjectDoesNotExist:
        raise VoltPyDoesNotExists()

    return voltpy_serve_csv(
        request=request,
        filedata=csv_file,
        filename=filename
    )


@redirect_on_voltpyexceptions
@with_user
def browseFilesets(request, user, page_number=1):
    sortableBy = (
        'id',
        'name',
        'owner',
        'date',
    )
    all_files = mmodels.Fileset.all()
    paginated = paginate(
        request=request,
        queryset=all_files,
        sortable_by=sortableBy,
        current_page=int(page_number)
    )
    files = paginated['current_page_content']
    context = {
        'user': user,
        'list_header': 'Filesets',
        'paginator': paginated,
        'when_empty': ''.join([
            "You have no files uploaded. ",
            "<a href='{url}'>Upload one</a>.".format(
                url=reverse('upload')
            ),
        ])
    }
    return voltpy_render(
        request=request,
        template_name='manager/browse.html',
        context=context
    )


@redirect_on_voltpyexceptions
@with_user
def browseFiles(request, user, page_number=1):
    sortable_by = (
        'id',
        'name',
        'analytes',
        'filename',
        'owner',
        'date'
    )
    all_files = mmodels.File.all()
    paginated = paginate(
        request=request,
        queryset=all_files,
        sortable_by=sortable_by,
        current_page=int(page_number)
    )
    context = {
        'user': user,
        'list_header': 'Files',
        'paginator': paginated,
        'when_empty': ''.join([
            "You have no files uploaded. ",
            "<a href='{url}'>Upload one</a>.".format(
                url=reverse('upload')
            ),
        ])
    }
    return voltpy_render(
        request=request,
        template_name='manager/browse.html',
        context=context
    )


@redirect_on_voltpyexceptions
@with_user
def browseAnalysis(request, user, page_number=1):
    all_anals = mmodels.Analysis.all()
    sortable_by = (
        'id',
        'name',
        'method',
        'dataset',
        'analytes',
        'owner',
        'date'
    )
    paginated = paginate(
        request=request,
        queryset=all_anals,
        sortable_by=sortable_by,
        current_page=int(page_number)
    )
    context = {
        'user': user,
        'list_header': 'Analysis',
        'paginator': paginated,
        'when_empty': ''.join([
            "Analysis can only be performed on the Dataset. ",
            "<a href='{url}'>Choose one</a>.".format(
                url=reverse('browseDatasets')
            ),
        ])
    }
    return voltpy_render(
        request=request,
        template_name='manager/browse.html',
        context=context
    )


@redirect_on_voltpyexceptions
@with_user
def browseDatasets(request, user, page_number=1):
    sortable_by = (
        'id',
        'name',
        'analytes',
        'owner',
        'date'
    )
    all_csets = mmodels.Dataset.all()
    paginated = paginate(
        request=request,
        queryset=all_csets,
        sortable_by=sortable_by,
        current_page=int(page_number)
    )
    context = {
        'user': user,
        'list_header': 'Datasets',
        'paginator': paginated,
        'when_empty': ''.join([
            "You have no Datasets. ",
            "<a href='{url}'>Prepare one</a>.".format(
                url=reverse('createDataset')
            ),
        ])
    }
    return voltpy_render(
        request=request,
        template_name='manager/browse.html',
        context=context
    )


@redirect_on_voltpyexceptions
@with_user
def deleteFileset(request, user, fileset_id):
    fs = mmodels.Fileset.get(id=fileset_id)
    onSuccess = reverse('browseFilesets')
    return delete_helper(
        request=request,
        user=user,
        item=fs,
        onSuccessRedirect=onSuccess
    )


@redirect_on_voltpyexceptions
@with_user
def deleteFile(request, user, file_id):
    cfile = mmodels.File.get(id=file_id)
    onSuccess = reverse('browseFiles')
    return delete_helper(
        request=request,
        user=user,
        item=cfile,
        onSuccessRedirect=onSuccess
    )


@redirect_on_voltpyexceptions
@with_user
def deleteCurve(request, user, obj_type, obj_id, to_delete_id):
    if obj_type == 'file':
        try:
            delete_fun = mmodels.File.get(id=int(obj_id)).curves_data.remove
            cd = mmodels.CurveData.objects.get(id=to_delete_id)  # get without permission checking, it is checked in remove func
        except ObjectDoesNotExist:
            raise VoltPyDoesNotExists('Object does not exists, too low permissions')
        redirect_to = reverse('showFile', args=[obj_id])
        return delete_helper(
            request=request,
            user=user,
            item=cd,
            delete_fun=delete_fun,
            onSuccessRedirect=redirect_to
        )
    else:  # dataset
        try:
            cd = mmodels.CurveData.objects.get(id=to_delete_id)
            delete_fun = mmodels.Dataset.get(id=obj_id).curves_data.remove
        except ObjectDoesNotExist:
            raise VoltPyDoesNotExists('Object does not exists, too low permissions')
        return delete_helper(
            request=request,
            user=user,
            item=cd,
            delete_fun=delete_fun,
            onSuccessRedirect=reverse('showDataset', args=[obj_id])
        )


@redirect_on_voltpyexceptions
@with_user
def deleteAnalysis(request, user, analysis_id):
    a = mmodels.Analysis.get(id=analysis_id)
    onSuccess = reverse('browseAnalysis')
    return delete_helper(
        request=request,
        user=user,
        item=a,
        onSuccessRedirect=onSuccess
    )


@redirect_on_voltpyexceptions
@with_user
def deleteDataset(request, user, dataset_id):
    a = mmodels.Dataset.get(id=dataset_id)
    onSuccess = reverse('browseDatasets')
    return delete_helper(
        request=request,
        user=user,
        item=a,
        onSuccessRedirect=onSuccess
    )


@redirect_on_voltpyexceptions
@with_user
def deleteFromDataset(request, user, dataset_id):
    cs = mmodels.Dataset.get(id=int(dataset_id))
    return deleteFromDatasetLike(request, user, cs)


@redirect_on_voltpyexceptions
@with_user
def deleteFromFile(request, user, file_id):
    cs = mmodels.File.get(id=int(file_id))
    return deleteFromDatasetLike(request, user, cs)


def deleteFromDatasetLike(request, user, cs):
    if request.method == 'POST':
        text = []
        if request.POST.get('confirm', False):
            confForm = mforms.GenericConfirmForm(request.POST)
            cdids = request.POST.get('cdids', '').split(',')
            cdids = list(map(int, cdids))
            if confForm.confirmed():
                cds = mmodels.CurveData.filter(id__in=cdids)
                for cd in cds.all():
                    cs.removeCurve(cd)
                cs.save()
                add_notification(request=request, text="Deleted")
                return HttpResponseRedirect(cs.getUrl())
            extra_data = ''.join([
                '<input type="hidden" name="cdids" value="',
                ','.join(map(str, cdids)),
                '" />'
            ])
            if len(cdids) > 0:
                cds = mmodels.CurveData.filter(id__in=cdids)
                text.append('Following curves will be removed from %s:<ul>' % cs)
                for cd in cds.all():
                    text.append('<li> %s </li>' % cd.curve.name)
                text.append('</ul>')
        else:
            to_del = []
            for pkey, pval in request.POST.items():
                if pkey.startswith('cd_'):
                    if pval == 'on':
                        to_del.append(int(pkey[3:]))
            text = []
            if len(to_del) > 0:
                cds = mmodels.CurveData.filter(id__in=to_del)
                text.append('Following curves will be removed from %s:<ul>' % cs)
                for cd in cds.all():
                    text.append('<li> %s </li>' % cd.curve.name)
                text.append('</ul>')
            extra_data = ''.join([
                '<input type="hidden" name="cdids" value="',
                ','.join(map(str, to_del)),
                '" />'
            ])

        confForm = mforms.GenericConfirmForm()

        context = {
            'text_to_confirm': ''.join(text),
            'hidden_values': extra_data,
            'form': confForm,
            'user': user,
        }

        return voltpy_render(
            request=request,
            template_name='manager/confirmGeneric.html',
            context=context
        )


@redirect_on_voltpyexceptions
@with_user
def createDataset(request, user, toCloneCF=[], toCloneCS=[]):
    """
    from pyinstrument import Profiler
    profiler = Profiler(use_signal=False)
    profiler.start()
    """

    if request.method == 'POST':
        form = mforms.SelectCurvesForDatasetForm(user, request.POST)
        if form.is_valid():
            dataset_id = form.process(user)
            if dataset_id is not False:
                if dataset_id > -1:
                    return HttpResponseRedirect(
                        reverse('showDataset', args=[dataset_id])
                    )
    else:
        form = mforms.SelectCurvesForDatasetForm(user, toCloneCS=toCloneCS, toCloneCF=toCloneCF)

    context = {
        'form_html': form.drawByHand(request),
        'user': user
    }
    ret = voltpy_render(
        request=request,
        template_name='manager/createDataset.html',
        context=context
    )
    """
    profiler.stop()
    print(profiler.output_text())
    """
    return ret


@redirect_on_voltpyexceptions
@with_user
def showAnalysis(request, user, analysis_id):
    an = mmodels.Analysis.get(id=analysis_id)

    if an.completed is False:
        return HttpResponseRedirect(reverse('analyze', args=[an.id]))

    form_data = {'model': an, 'label_name': ''}
    form_ret = form_helper(
        user=user,
        request=request,
        formClass=mforms.EditName,
        submitName='anEditName',
        submitText='Save',
        formExtraData=form_data
    )

    mm = mmm.MethodManager(user=user, analysis_id=analysis_id)
    info = mm.getFinalContent(request=request, user=user)
    plotScr, plotDiv, butDiv = generate_plot(
        request=request,
        user=user,
        to_plot=an.dataset
    )
    if mm.methodCanBeApplied():
        applyClass = '_voltJS_applyModel _voltJS_model@' + str(an.id)
    else:
        applyClass = '_disabled'
    if an.owner == user:
        share_button = '_voltJS_requestLink'
    else:
        share_button = '_disabled'

    context = {
        'user': user,
        'scripts': plotScr,
        'head': info.get('head', ''),
        'main_plot': plotDiv,
        'main_plot_buttons': butDiv,
        'showing': an,
        'disp_name_edit': form_ret['html'],
        'text': info.get('body', ''),
        'back_to_browse_button': get_redirect_class(
            reverse('browseAnalysis')
        ),
        'curve_set_button': get_redirect_class(
            reverse('showDataset', args=[
                an.dataset.id
            ])
        ),
        'export_data_button': get_redirect_class(
            reverse('export', kwargs={
                'obj_type': 'analysis',
                'obj_id': an.id,
            })
        ),
        'share_button': share_button,
        'undo_button': '_disabled',
        'apply_model_to': applyClass
    }
    return voltpy_render(
        request=request,
        template_name='manager/showAnalysis.html',
        context=context
    )


@redirect_on_voltpyexceptions
@with_user
def searchDataset(request, user):
    if request.method != 'POST':
        return JsonResponse({})
    searchStr = request.POST.get('search', '')
    css = []
    if searchStr == '':
        css = mmodels.Dataset.all()
    else:
        if is_number(searchStr):
            cs_id = float(searchStr)
            css.extend(mmodels.Dataset.filter(id=cs_id))
        css.extend(mmodels.Dataset.filter(name__icontains=searchStr))

    ret = {}
    for cs in css:
        ret[cs.id] = cs.__str__()
    return JsonResponse({'result': ret})


@redirect_on_voltpyexceptions
@with_user
def showProcessed(request, user, processing_id):
    try:
        cf = mmodels.Processing.get(id=processing_id)
    except ObjectDoesNotExist:
        cf = None
    context = {
        'user': user,
        'processing': processing_id,
    }
    return voltpy_render(
        request=request,
        template_name='manager/showAnalysis.html',
        context=context
    )


@redirect_on_voltpyexceptions
@with_user
def showFileset(request, user, fileset_id):
    fs = mmodels.Fileset.get(id=fileset_id)

    form_data = {'model': fs, 'label_name': ''}
    edit_name_form = form_helper(
        user=user,
        request=request,
        formClass=mforms.EditName,
        submitName='anEditName',
        submitText='Save',
        formExtraData=form_data
    )

    plotScr, plotDiv, butDiv = generate_plot(
        request=request,
        user=user,
        to_plot=fs
    )
    if fs.owner == user:
        share_button = '_voltJS_requestLink'
    else:
        share_button = '_disabled'

    context = {
        'scripts': plotScr,  # + formAnalyze.getJS(request) + formProcess.getJS(request),
        'main_plot': plotDiv,
        'main_plot_buttons': butDiv,
        'user': user,
        'disp_name_edit': edit_name_form['html'],
        'showing': fs,
        'export_data_button': get_redirect_class(
            reverse('export', kwargs={
                'obj_type': 'fileset',
                'obj_id': fs.id,
            })
        ),
        'delete_button': get_redirect_class(
            reverse('deleteFileset', kwargs={
                'fileset_id': fs.id
            })
        ),
        'curve_set_button': get_redirect_class(
            reverse('cloneFileset', kwargs={
                'to_clone_id': fs.id
            })
        ),
        'undo_button': '_disabled',
        'share_button': share_button,
        'back_to_browse_button': get_redirect_class(
            reverse('browseFilesets')
        )
    }
    return voltpy_render(
        request=request,
        template_name='manager/showFileset.html',
        context=context
    )


@redirect_on_voltpyexceptions
@with_user
def undoDataset(request, user, dataset_id):
    try:
        cs = mmodels.Dataset.get(id=dataset_id)
    except ObjectDoesNotExist:
        raise VoltPyDoesNotExists()

    if request.method == "POST" and request.POST.get('confirm', False):
        confForm = mforms.GenericConfirmForm(request.POST)
        if confForm.confirmed():
            cs.undo()
            add_notification(request, 'Changes undone.')
            return HttpResponseRedirect(cs.getUrl())
        else:
            add_notification(request, 'Check the checkbox to confirm.', 1)

    else:
        confForm = mforms.GenericConfirmForm()

    context = {
        'text_to_confirm': 'This will undo changes to Dataset {0}'.format(cs),
        'form': confForm,
        'user': user,
    }

    return voltpy_render(
        request=request,
        template_name='manager/confirmGeneric.html',
        context=context
    )


@redirect_on_voltpyexceptions
@with_user
def showDataset(request, user, dataset_id):
    cs = mmodels.Dataset.get(id=dataset_id)

    form_data = {'model': cs, 'label_name': ''}
    edit_name_form = form_helper(
        user=user,
        request=request,
        formClass=mforms.EditName,
        submitName='anEditName',
        submitText='Save',
        formExtraData=form_data
    )

    plotScr, plotDiv, butDiv = generate_plot(
        request=request,
        user=user,
        to_plot=cs
    )

    import manager.analytesTable as at
    at_disp = at.analytesTable(cs, obj_type='dataset')

    mm = mmm.MethodManager(user=user, dataset_id=dataset_id)
    if request.method == 'POST':
        if 'startAnalyze' in request.POST:
            formAnalyze = mm.getAnalysisSelectionForm(request.POST, dataset=cs)
            if formAnalyze.is_valid():
                analyzeid = formAnalyze.process(user, cs)
                return HttpResponseRedirect(reverse('analyze', args=[analyzeid]))
        else:
            formAnalyze = mm.getAnalysisSelectionForm(dataset=cs)

        if all([
            not cs.locked,
            'startProcessing' in request.POST
        ]):
            formProcess = mm.getProcessingSelectionForm(request.POST, dataset=cs)
            if formProcess.is_valid():
                procid = formProcess.process(user, cs)
                return HttpResponseRedirect(reverse('process', args=[procid]))
        else:
            formProcess = mm.getProcessingSelectionForm(dataset=cs, disabled=cs.locked)

    else:
        formAnalyze = mm.getAnalysisSelectionForm(dataset=cs)
        formProcess = mm.getProcessingSelectionForm(dataset=cs, disabled=cs.locked)

    if cs.owner == user:
        share_button = '_voltJS_requestLink'
    else:
        share_button = '_disabled'
    if cs.hasUndo():
        undo_button = get_redirect_class(
            reverse('undoDataset', kwargs={
                'dataset_id': cs.id,
            })
        )
    else:
        undo_button = '_disabled'
    if not cs.locked:
        add_analyte = get_redirect_class(
            reverse('editAnalyte', kwargs={
                'obj_type': 'dataset',
                'obj_id': cs.id,
                'analyte_id': 'new'
            })
        )
    else:
        add_analyte = '_disabled'
    context = {
        'scripts': plotScr + formAnalyze.getJS(request) + formProcess.getJS(request),
        'main_plot': plotDiv,
        'main_plot_buttons': butDiv,
        'user': user,
        'disp_name_edit': edit_name_form['html'],
        'at': at_disp,
        'formProcess': formProcess,
        'formAnalyze': formAnalyze,
        'showing': cs,
        'back_to_browse_button': get_redirect_class(
            reverse('browseDatasets')
        ),
        'delete_button': get_redirect_class(
            reverse('deleteDataset', args=[
                cs.id
            ])
        ),
        'share_button': share_button,
        'export_data_button': get_redirect_class(
            reverse('export', kwargs={
                'obj_type': 'dataset',
                'obj_id': cs.id,
            })
        ),
        'undo_button': undo_button,
        'edit_curves_button':get_redirect_class(
            reverse('editCurves', kwargs={
                'obj_type': 'dataset',
                'obj_id': cs.id,
            })
        ),
        'curve_set_button': get_redirect_class(
            reverse('cloneDataset', kwargs={
                'to_clone_id': cs.id,
            })
        ),
        'add_analyte_button': add_analyte,
    }
    return voltpy_render(
        request=request,
        template_name='manager/showDataset.html',
        context=context
    )


@redirect_on_voltpyexceptions
@with_user
def cloneDataset(request, user, to_clone_id):
    toCloneCS = mmodels.Dataset.get(id=int(to_clone_id))
    newcs = toCloneCS.getCopy()
    add_notification(request, 'Dataset cloned. Redirected to the new Dataset.')
    return HttpResponseRedirect(newcs.getUrl())


@redirect_on_voltpyexceptions
@with_user
def cloneFileset(request, user, to_clone_id):
    toCloneCS = mmodels.Fileset.get(id=int(to_clone_id))
    newcs = toCloneCS.getNewDataset()
    add_notification(request, 'Fileset copied as a new Dataset. Redirected to the new Dataset.')
    return HttpResponseRedirect(newcs.getUrl())


@redirect_on_voltpyexceptions
@with_user
def cloneFile(request, user, to_clone_id):
    toCloneCS = mmodels.File.get(id=int(to_clone_id))
    newcs = toCloneCS.getNewDataset()
    add_notification(request, 'File copied as a new Dataset. Redirected to the new Dataset.')
    return HttpResponseRedirect(newcs.getUrl())


@redirect_on_voltpyexceptions
@with_user
def upload(request, user):
    can_upload = user.groups.filter(name='registered_users').exists()
    context = {
        'user': user,
        'can_upload': can_upload,
        'allowedExt': ', '.join(umanager.allowedExt),
    }
    return voltpy_render(
        request=request,
        template_name='manager/uploadFileset.html',
        context=context
    )


@redirect_on_voltpyexceptions
@with_user
def showFile(request, user, file_id):
    cf = mmodels.File.get(id=int(file_id))

    form_data = {'model': cf, 'label_name': ''}
    edit_name_form = form_helper(
        user=user,
        request=request,
        formClass=mforms.EditName,
        submitName='anEditName',
        submitText='Save',
        formExtraData=form_data
    )

    import manager.analytesTable as at
    plotScr, plotDiv, butDiv = generate_plot(
        request=request,
        user=user,
        to_plot=cf
    )

    at_disp = at.analytesTable(cf, obj_type='file')
    if cf.owner == user:
        share_button = '_voltJS_requestLink'
    else:
        share_button = '_disabled'

    add_analyte = get_redirect_class(
        reverse('editAnalyte', kwargs={
            'obj_type': 'file',
            'obj_id': cf.id,
            'analyte_id': 'new'
        })
    )
    context = {
        'scripts': plotScr,
        'main_plot': plotDiv,
        'main_plot_buttons': butDiv,
        'user': user,
        'showing': cf,
        'disp_name_edit': edit_name_form['html'],
        'at': at_disp,
        'export_data_button': get_redirect_class(
            reverse('export', kwargs={
                'obj_type': 'file',
                'obj_id': cf.id,
            })
        ),
        'curve_set_button': get_redirect_class(
            reverse('cloneFile', kwargs={
                'to_clone_id': cf.id,
            })
        ),
        'delete_button': get_redirect_class(
            reverse('deleteFile', args=[
                cf.id
            ])
        ),
        'undo_button': '_disabled',
        'share_button': share_button,
        'back_to_browse_button': get_redirect_class(
            reverse('browseFiles')
        ),
        'edit_curves_button':get_redirect_class(
            reverse('editCurves', kwargs={
                'obj_type': 'file',
                'obj_id': cf.id,
            })
        ),
        'add_analyte_button': add_analyte
    }
    return voltpy_render(
        request=request,
        template_name='manager/showFile.html',
        context=context
    )


@redirect_on_voltpyexceptions
@with_user
def applyModel(request, user, obj_type, obj_id, dataset_id):
    if obj_type == 'an':
        mm = mmm.MethodManager(user=user, analysis_id=obj_id)
    elif obj_type == 'pr':
        mm = mmm.MethodManager(user=user, processing_id=obj_id)

    if request.method == "POST" and request.POST.get('confirm', False):
        confForm = mforms.GenericConfirmForm(request.POST)
        if confForm.confirmed():
            return HttpResponseRedirect(
                mm.applyTo(
                    user=user,
                    request=request,
                    dataset_id=dataset_id
                )
            )
        else:
            add_notification(request, 'Check the checkbox to confirm.', 1)

    else:
        confForm = mforms.GenericConfirmForm()

    context = {
        'text_to_confirm': 'This will apply model {model} to dataset {cs}'.format(
            model=obj_id,
            cs=dataset_id
        ),
        'form': confForm,
        'user': user,
    }
    return voltpy_render(
        request=request,
        template_name='manager/confirmGeneric.html',
        context=context
    )


@redirect_on_voltpyexceptions
@with_user
def editCurves(request, user, obj_type, obj_id):
    if obj_type == 'file':
        cs = mmodels.File.get(id=obj_id)
    elif obj_type == 'dataset':
        cs = mmodels.Dataset.get(id=obj_id)
    else:
        raise VoltPyNotAllowed

    if request.method == 'POST':
        form = mforms.EditCurvesForm(user, cs, request.POST)
        if form.is_valid():
            if form.process(user) is True:
                if obj_type == 'file':
                    return HttpResponseRedirect(
                        reverse('showFile', args=[obj_id])
                    )
                else:
                    return HttpResponseRedirect(
                        reverse('showDataset', args=[obj_id])
                    )
    else:
        form = mforms.EditCurvesForm(user, cs)

    if obj_type == 'file':
        plotType = 'file'
        dispType = 'file'
    else:
        plotType = 'dataset'
        dispType = 'dataset'
    plotScr, plotDiv, butDiv = generate_plot(
        request=request,
        user=user,
        plot_type=plotType,
        value_id=obj_id
    )

    infotext = 'Editing curves in '.format(cs.name)

    context = {
        'scripts': plotScr,
        'main_plot': plotDiv,
        'main_plot_buttons': butDiv,
        'user': user,
        'obj_name': dispType,
        'obj_id': obj_id,
        'form': form,
        'infotext': ''.join([
            infotext,
            dispType,
        ])
    }
    return voltpy_render(
        request=request,
        template_name='manager/editAnalyte.html',
        context=context
    )


@redirect_on_voltpyexceptions
@with_user
def editAnalyte(request, user, obj_type, obj_id, analyte_id):
    if obj_type == 'file':
        cs = mmodels.File.get(id=obj_id)
    elif obj_type == 'dataset':
        cs = mmodels.Dataset.get(id=obj_id)
    else:
        raise VoltPyNotAllowed

    if request.method == 'POST':
        form = mforms.EditAnalytesForm(user, cs, analyte_id, request.POST)
        if form.is_valid():
            if form.process(user) is True:
                return HttpResponseRedirect(
                    cs.getUrl()
                )
    else:
        form = mforms.EditAnalytesForm(user, cs, analyte_id)

    if obj_type == 'file':
        plotType = 'file'
        dispType = 'file'
    else:
        plotType = 'dataset'
        dispType = 'dataset'
    plotScr, plotDiv, butDiv = generate_plot(
        request=request,
        user=user,
        plot_type=plotType,
        value_id=obj_id
    )

    if analyte_id == 'new':
        infotext = 'Adding new analyte for '
    else:
        try:
            analyte = mmodels.Analyte.get(id=analyte_id)
        except ObjectDoesNotExist:
            infotext = 'Adding new analyte for '
        infotext = 'Editing {0} in '.format(analyte.name)

    context = {
        'scripts': plotScr,
        'main_plot': plotDiv,
        'main_plot_buttons': butDiv,
        'user': user,
        'obj_name': dispType,
        'obj_id': obj_id,
        'form': form,
        'infotext': ''.join([
            infotext,
            dispType,
            ' {0}'.format(cs)
        ])
    }
    return voltpy_render(
        request=request,
        template_name='manager/editAnalyte.html',
        context=context
    )


@redirect_on_voltpyexceptions
@with_user
def analyze(request, user, analysis_id):
    mm = mmm.MethodManager(user=user, analysis_id=analysis_id)
    mm.process(request=request, user=user)
    return mm.getStepContent(request=request, user=user)


@redirect_on_voltpyexceptions
@with_user
def process(request, user, processing_id):
    mm = mmm.MethodManager(user=user, processing_id=processing_id)
    mm.process(request=request, user=user)
    return mm.getStepContent(request=request, user=user)


@with_user
def plotInteraction(request, user):
    if any([
        request.method != 'POST',
        not request.POST.get('query', None)
    ]):
        return HttpResponse('Error')

    ret = ''
    if request.POST.get('query') == 'methodmanager':
        vtype = request.POST.get('vtype', '')
        vid = int(request.POST.get('vid', -1))
        kwrg = {
            vtype: vid
        }
        mm = mmm.MethodManager(user=user, **kwrg)
        mm.process(request=request, user=user)
        ret = mm.ajax(user=user)
    elif request.POST.get('query') == 'plotmanager':
        import manager.plotmanager as mpm
        pm = mpm.PlotManager()
        ret = pm.plotInteraction(request=request, user=user)
    else:
        raise NameError('Unknown query type')
    return JsonResponse(ret)


@redirect_on_voltpyexceptions
@with_user
def unshare(request, user, share_id):
    share = mmodels.SharedLink.get(id=int(share_id))

    def deleteFun(share):
        obj = get_shared_object(share)
        share.delete()
        for u in share.users.all():
            remove_perm(share.permissions, u, obj)

    return delete_helper(
        request=request,
        user=user,
        item=share,
        delete_fun=deleteFun,
        onSuccessRedirect=reverse('settings')
    )


@redirect_on_voltpyexceptions
def shareLink(request, link_hash):
    import random
    import string
    from guardian.shortcuts import assign_perm
    try:
        shared_link = mmodels.SharedLink.objects.get(link=link_hash)
    except ObjectDoesNotExist as e:
        raise VoltPyDoesNotExists

    obj = get_shared_object(shared_link)

    try:
        user = request.User
    except:
        user = None
    if user is None:
        random = ''.join([
            random.choice(string.ascii_letters + string.digits) for n in range(32)
        ])
        while User.objects.filter(username='temp_' + random).exists():
            random = ''.join([
                random.choice(string.ascii_letters + string.digits) for n in range(32)
            ])
        user = User.objects.create_user('temp_' + random, 'temp@voltammetry.center', 'xxx')
        user.is_active = True
        user.save()
        group = Group.objects.get(name='temp_users')
        group.user_set.add(user)
        group.save()
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    
    assign_perm(shared_link.permissions, user, obj)
    shared_link.addUser(user)
    return HttpResponseRedirect(obj.getUrl())


@redirect_on_voltpyexceptions
@with_user
def getShareable(request, user):
    try:
        if request.method != 'POST':
            return
        to_share = request.POST['to_share']
        to_share = to_share.split('/')
        obj_id = int(to_share[-2])
        obj_type = to_share[-3]
        if obj_type == 'show-dataset':
            obj = mmodels.Dataset.get(id=obj_id)
        elif obj_type == 'show-file':
            obj = mmodels.File.get(id=obj_id)
        elif obj_type == 'show-fileset':
            obj = mmodels.Fileset.get(id=obj_id)
        elif obj_type == 'show-analysis':
            obj = mmodels.Analysis.get(id=obj_id)
        else:
            raise VoltPyNotAllowed('Unknown origin url.')
        link_rw = generate_share_link(user, 'rw', obj)
        link_ro = generate_share_link(user, 'ro', obj)
        return JsonResponse({'link_ro': link_ro, 'link_rw': link_rw})
    except Exception as e:
        print(e)
        return JsonResponse({'link_ro': 'Cannot share', 'link_rw': 'Cannot share'})
