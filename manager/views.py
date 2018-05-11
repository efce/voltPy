import json
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
from manager.helpers.functions import generate_share_link
from manager.helpers.functions import paginate
from manager.helpers.decorators import with_user
from manager.helpers.decorators import redirect_on_voltpyexceptions


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


def account_activation_sent(request):
    context = {'user': None}
    return voltpy_render(
        request=request,
        template_name='registration/account_activation_sent.html',
        context=context
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
def export(request, user, objType, objId):
    allowedTypes = ('fs', 'cf', 'cs', 'an')
    assert objType in allowedTypes
    try:
        csvFile = ''
        filename = 'export_%s.csv'
        if objType == 'fs':
            fs = mmodels.FileSet.get(id=int(objId), deleted=False)
            csvFile = fs.export()
            filename = filename % fs.name
        elif objType == 'cf':
            cf = mmodels.FileCurveSet.get(id=int(objId))
            csvFile = cf.export()
            filename = filename % cf.name
        elif objType == 'cs':
            cs = mmodels.CurveSet.get(id=int(objId))
            csvFile = cs.export()
            filename = filename % cs.name
        elif objType == 'an':
            mm = mmm.MethodManager(user=user, analysis_id=objId)
            csvFile, modelName = mm.exportFile()
            filename = 'analysis_%s.csv' % (modelName if modelName else ('id_%s' % objId))
    except ObjectDoesNotExist:
        raise VoltPyDoesNotExists()

    return voltpy_serve_csv(
        request=request,
        filedata=csvFile,
        filename=filename
    )


@redirect_on_voltpyexceptions
@with_user
def browseFileSets(request, user, page_number=1):
    sortableBy = (
        'id',
        'name',
        'owner',
        'date',
    )
    all_files = mmodels.FileSet.all()
    paginated = paginate(
        request=request,
        queryset=all_files,
        sortable_by=sortableBy,
        current_page=int(page_number)
    )
    files = paginated['current_page_content']
    context = {
        'user': user,
        'list_header': 'Files Sets:',
        'list_to_disp': files,
        'paginator': paginated['paginator'],
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
def browseCurveFiles(request, user, page_number=1):
    sortable_by = (
        'id',
        'name',
        'fileName',
        'owner',
        'date'
    )
    all_files = mmodels.FileCurveSet.all()
    paginated = paginate(
        request=request,
        queryset=all_files,
        sortable_by=sortable_by,
        current_page=int(page_number)
    )
    context = {
        'user': user,
        'list_header': 'Files:',
        'list_to_disp': paginated['current_page_content'],
        'paginator': paginated['paginator'],
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
        'list_header': 'Analysis:',
        'list_to_disp': paginated['current_page_content'],
        'paginator': paginated['paginator'],
        'when_empty': ''.join([
            "Analysis can only be performed on the CurveSet. ",
            "<a href='{url}'>Choose one</a>.".format(
                url=reverse('browseCurveSets')
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
def browseCurveSet(request, user, page_number=1):
    sortable_by = (
        'id',
        'name',
        'owner',
        'date'
    )
    all_csets = mmodels.CurveSet.all()
    paginated = paginate(
        request=request,
        queryset=all_csets,
        sortable_by=sortable_by,
        current_page=int(page_number)
    )
    context = {
        'user': user,
        'list_header': 'Curve Sets:',
        'list_to_disp': paginated['current_page_content'],
        'paginator': paginated['paginator'],
        'when_empty': ''.join([
            "You have no CurveSets. ",
            "<a href='{url}'>Prepare one</a>.".format(
                url=reverse('createCurveSet')
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
def deleteFileSet(request, user, fileset_id):
    try:
        fs = mmodels.FileSet.get(id=fileset_id)
    except ObjectDoesNotExist:
        fs = None
    onSuccess = reverse('browseFileSets')
    return delete_helper(
        request=request,
        user=user,
        item=fs,
        onSuccessRedirect=onSuccess
    )


@redirect_on_voltpyexceptions
@with_user
def deleteCurveFile(request, user, file_id):
    try:
        cfile = mmodels.FileCurveSet.get(id=file_id)
    except ObjectDoesNotExist:
        cfile = None
    onSuccess = reverse('browseCurveFiles')
    return delete_helper(
        request=request,
        user=user,
        item=cfile,
        onSuccessRedirect=onSuccess
    )


@redirect_on_voltpyexceptions
@with_user
def deleteCurve(request, user, objType, objId, delId):
    if objType == 'cf':
        try:
            delete_fun = mmodels.FileCurveSet.get(id=int(objId)).curvesData.remove
            cd = mmodels.CurveData.objects.get(id=delId)  # get without permission checking, it is checked in remove func
        except ObjectDoesNotExist:
            raise VoltPyDoesNotExists('Object does not exists, too low permissions')
        redirect_to = reverse('showCurveFile', args=[objId])
        return delete_helper(
            request=request,
            user=user,
            item=cd,
            delete_fun=delete_fun,
            onSuccessRedirect=redirect_to
        )
    else:  # curveset
        try:
            cd = mmodels.CurveData.objects.get(id=delId)
            delete_fun = mmodels.CurveSet.get(id=objId).curvesData.remove
        except ObjectDoesNotExist:
            raise VoltPyDoesNotExists('Object does not exists, too low permissions')
        return delete_helper(
            request=request,
            user=user,
            item=cd,
            delete_fun=delete_fun,
            onSuccessRedirect=reverse('showCurveSet', args=[objId])
        )


@redirect_on_voltpyexceptions
@with_user
def deleteAnalysis(request, user, analysis_id):
    try:
        a = mmodels.Analysis.get(id=analysis_id)
    except ObjectDoesNotExist:
        a = None
    onSuccess = reverse('browseAnalysis')
    return delete_helper(
        request=request,
        user=user,
        item=a,
        onSuccessRedirect=onSuccess
    )


@redirect_on_voltpyexceptions
@with_user
def deleteCurveSet(request, user, curveset_id):
    try:
        a = mmodels.CurveSet.get(id=curveset_id)
    except ObjectDoesNotExist:
        a = None
    onSuccess = reverse('browseCurveSets')
    return delete_helper(
        request=request,
        user=user,
        item=a,
        onSuccessRedirect=onSuccess
    )


@redirect_on_voltpyexceptions
@with_user
def createCurveSet(request, user, toCloneCF=[], toCloneCS=[]):
    """
    from pyinstrument import Profiler
    profiler = Profiler(use_signal=False)
    profiler.start()
    """

    if request.method == 'POST':
        form = mforms.SelectCurvesForCurveSetForm(user, request.POST)
        if form.is_valid():
            cs_id = form.process(user)
            if cs_id is not False:
                if cs_id > -1:
                    return HttpResponseRedirect(
                        reverse('showCurveSet', args=[cs_id])
                    )
    else:
        form = mforms.SelectCurvesForCurveSetForm(user, toCloneCS=toCloneCS, toCloneCF=toCloneCF)

    context = {
        'form_html': form.drawByHand(request),
        'user': user
    }
    ret = voltpy_render(
        request=request,
        template_name='manager/createCurveSet.html',
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
    try:
        an = mmodels.Analysis.get(id=analysis_id)
    except ObjectDoesNotExist:
        raise VoltPyNotAllowed(user)

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
        to_plot=an.curveSet
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
            reverse('showCurveSet', args=[
                an.curveSet.id
            ])
        ),
        'export_data': get_redirect_class(
            reverse('export', kwargs={
                'objType': 'an',
                'objId': an.id,
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
def searchCurveSet(request, user):
    if request.method != 'POST':
        return JsonResponse({})
    searchStr = request.POST.get('search', '')
    css = []
    if searchStr == '':
        css = mmodels.CurveSet.all()
    else:
        if is_number(searchStr):
            cs_id = float(searchStr)
            css.extend(mmodels.CurveSet.filter(id=cs_id))
        css.extend(mmodels.CurveSet.filter(name__icontains=searchStr))

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
def showFileSet(request, user, fileset_id):
    try:
        fs = mmodels.FileSet.get(id=fileset_id)
    except ObjectDoesNotExist:
        raise VoltPyDoesNotExists()

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
                'objType': 'fs',
                'objId': fs.id,
            })
        ),
        'curve_set_button': get_redirect_class(
            reverse('cloneFileSet', kwargs={
                'toCloneId': fs.id
            })
        ),
        'undo_button': '_disabled',
        'share_button': share_button,
        'back_to_browse_button': get_redirect_class(
            reverse('browseFileSets')
        )
    }
    return voltpy_render(
        request=request,
        template_name='manager/showFileSet.html',
        context=context
    )


@redirect_on_voltpyexceptions
@with_user
def undoCurveSet(request, user, curveset_id):
    try:
        cs = mmodels.CurveSet.get(id=curveset_id)
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
        'text_to_confirm': 'This will undo changes to CurveSet {0}'.format(cs.id),
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
def showCurveSet(request, user, curveset_id):
    try:
        cs = mmodels.CurveSet.get(id=curveset_id)
    except ObjectDoesNotExist:
        raise VoltPyDoesNotExists()

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
    at_disp = at.analytesTable(cs, objType='cs')

    mm = mmm.MethodManager(user=user, curveset_id=curveset_id)
    if request.method == 'POST':
        if 'startAnalyze' in request.POST:
            formAnalyze = mm.getAnalysisSelectionForm(request.POST)
            if formAnalyze.is_valid():
                analyzeid = formAnalyze.process(user, cs)
                return HttpResponseRedirect(reverse('analyze', args=[analyzeid]))
        else:
            formAnalyze = mm.getAnalysisSelectionForm()

        if all([
            not cs.locked,
            'startProcessing' in request.POST
        ]):
            formProcess = mm.getProcessingSelectionForm(request.POST)
            if formProcess.is_valid():
                procid = formProcess.process(user, cs)
                return HttpResponseRedirect(reverse('process', args=[procid]))
        else:
            formProcess = mm.getProcessingSelectionForm(disabled=cs.locked)

    else:
        formAnalyze = mm.getAnalysisSelectionForm()
        formProcess = mm.getProcessingSelectionForm(disabled=cs.locked)

    if cs.owner == user:
        share_button = '_voltJS_requestLink'
    else:
        share_button = '_disabled'
    if cs.hasUndo():
        undo_button = get_redirect_class(
            reverse('undoCurveSet', kwargs={
                'curveset_id': cs.id,
            })
        )
    else:
        undo_button = '_disabled'
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
            reverse('browseCurveSets')
        ),
        'delete_button': get_redirect_class(
            reverse('deleteCurveSet', args=[
                cs.id
            ])
        ),
        'share_button': share_button,
        'export_data_button': get_redirect_class(
            reverse('export', kwargs={
                'objType': 'cs',
                'objId': cs.id,
            })
        ),
        'undo_button': undo_button,
        'curve_set_button': get_redirect_class(
            reverse('cloneCurveSet', kwargs={
                'toCloneId': cs.id,
            })
        ),
    }
    return voltpy_render(
        request=request,
        template_name='manager/showCurveSet.html',
        context=context
    )


@redirect_on_voltpyexceptions
@with_user
def cloneCurveSet(request, user, toCloneId):
    toCloneCS = mmodels.CurveSet.get(id=int(toCloneId))
    newcs = toCloneCS.getCopy()
    add_notification(request, 'CurveSet cloned. Redirecting to the new CurveSet.')
    return HttpResponseRedirect(newcs.getUrl())


@redirect_on_voltpyexceptions
@with_user
def cloneFileSet(request, user, toCloneId):
    toCloneCS = mmodels.FileSet.get(id=int(toCloneId))
    newcs = toCloneCS.getNewCurveSet()
    add_notification(request, 'FileSet copied as a new CurveSet. Redirecting to the new CurveSet.')
    return HttpResponseRedirect(newcs.getUrl())


@redirect_on_voltpyexceptions
@with_user
def cloneCurveFile(request, user, toCloneId):
    toCloneCS = mmodels.FileCurveSet.get(id=int(toCloneId))
    newcs = toCloneCS.getNewCurveSet()
    add_notification(request, 'File copied as a new CurveSet. Redirecting to the new CurveSet.')
    return HttpResponseRedirect(newcs.getUrl())


@redirect_on_voltpyexceptions
@with_user
def upload(request, user):
    can_upload = user.groups.filter(name='registered_users').exists()
    context = {
        'user': user,
        'can_upload': can_upload,
        'allowedExt': umanager.allowedExt,
    }
    return voltpy_render(
        request=request,
        template_name='manager/uploadFile.html',
        context=context
    )


@redirect_on_voltpyexceptions
@with_user
def showCurveFile(request, user, file_id):
    try:
        cf = mmodels.FileCurveSet.get(id=int(file_id))
    except ObjectDoesNotExist:
        raise VoltPyNotAllowed(user)

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

    at_disp = at.analytesTable(cf, objType='cf')
    if cf.owner == user:
        share_button = '_voltJS_requestLink'
    else:
        share_button = '_disabled'

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
                'objType': 'cf',
                'objId': cf.id,
            })
        ),
        'curve_set_button': get_redirect_class(
            reverse('cloneCurveFile', kwargs={
                'toCloneId': cf.id,
            })
        ),
        'delete_button': get_redirect_class(
            reverse('deleteCurveFile', args=[
                cf.id
            ])
        ),
        'undo_button': '_disabled',
        'share_button': share_button,
        'back_to_browse_button': get_redirect_class(
            reverse('browseCurveFiles')
        )
    }
    return voltpy_render(
        request=request,
        template_name='manager/showFile.html',
        context=context
    )


@redirect_on_voltpyexceptions
@with_user
def applyModel(request, user, objType, objId, curveset_id):
    if objType == 'an':
        mm = mmm.MethodManager(user=user, analysis_id=objId)
    elif objType == 'pr':
        mm = mmm.MethodManager(user=user, processing_id=objId)

    if request.method == "POST" and request.POST.get('confirm', False):
        confForm = mforms.GenericConfirmForm(request.POST)
        if confForm.confirmed():
            return HttpResponseRedirect(
                mm.applyTo(
                    user=user,
                    request=request,
                    curveset_id=curveset_id
                )
            )
        else:
            add_notification(request, 'Check the checkbox to confirm.', 1)

    else:
        confForm = mforms.GenericConfirmForm()

    context = {
        'text_to_confirm': 'This will apply model {model} to curveset {cs}'.format(
            model=objId,
            cs=curveset_id
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
def editAnalyte(request, user, objType, objId, analyteId):
    if objType == 'cf':
        try:
            cs = mmodels.FileCurveSet.get(id=objId)
        except ObjectDoesNotExist:
            raise VoltPyNotAllowed

    elif objType == 'cs':
        try:
            cs = mmodels.CurveSet.get(id=objId)
        except ObjectDoesNotExist:
            raise VoltPyNotAllowed

    else:
        raise VoltPyNotAllowed

    if request.method == 'POST':
        form = mforms.EditAnalytesForm(user, cs, analyteId, request.POST)
        if form.is_valid():
            if form.process(user) is True:
                if objType == 'cf':
                    return HttpResponseRedirect(
                        reverse('showCurveFile', args=[objId])
                    )
                else:
                    return HttpResponseRedirect(
                        reverse('showCurveSet', args=[objId])
                    )
    else:
        form = mforms.EditAnalytesForm(user, cs, analyteId)

    if objType == 'cf':
        plotType = 'file'
        dispType = 'File'
    else:
        plotType = 'curveset'
        dispType = 'CurveSet'
    plotScr, plotDiv, butDiv = generate_plot(
        request=request,
        user=user,
        plot_type=plotType,
        value_id=objId
    )

    if analyteId == 'new':
        infotext = 'Adding new analyte in '
    else:
        try:
            analyte = mmodels.Analyte.get(id=analyteId)
        except ObjectDoesNotExist:
            infotext = 'Adding new analyte in '
        infotext = 'Editing {0} in '.format(analyte.name)

    context = {
        'scripts': plotScr,
        'main_plot': plotDiv,
        'main_plot_buttons': butDiv,
        'user': user,
        'obj_name': dispType,
        'obj_id': objId,
        'form': form,
        'infotext': ''.join([
            infotext,
            dispType,
            ' #{0}'.format(objId)
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
def shareLink(request, link_hash):
    import random
    import string
    from guardian.shortcuts import assign_perm
    try:
        shared_link = mmodels.SharedLink.objects.get(link=link_hash)
    except ObjectDoesNotExist as e:
        raise VoltPyDoesNotExists

    importlib = __import__('importlib')
    load_models = importlib.import_module('manager.models')
    obj_class = getattr(load_models, shared_link.object_type)
    try:
        obj = obj_class.objects.get(id=shared_link.object_id)
    except ObjectDoesNotExist as e:
        raise VoltPyDoesNotExists

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
        objId = int(to_share[-2])
        objType = to_share[-3]
        if objType == 'show-curveset':
            obj = mmodels.CurveSet.get(id=objId)
        elif objType == 'show-file':
            obj = mmodels.FileCurveSet.get(id=objId)
        elif objType == 'show-fileset':
            obj = mmodels.FileSet.get(id=objId)
        elif objType == 'show-analysis':
            obj = mmodels.Analysis.get(id=objId)
        else:
            raise VoltPyNotAllowed('Unknown origin url.')
        link_rw = generate_share_link(user, 'rw', obj)
        link_ro = generate_share_link(user, 'ro', obj)
        return JsonResponse({'link_ro': link_ro, 'link_rw': link_rw})
    except Exception as e:
        print(e)
        return JsonResponse({'link_ro': 'Cannot share', 'link_rw': 'Cannot share'})
