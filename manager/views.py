import json
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
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
from manager.helpers.decorators import with_user
from manager.helpers.decorators import redirect_on_voltpyexceptions


def signin(request):
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
                'domain': current_site.domain,
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
            cf = mmodels.CurveFile.get(id=int(objId), deleted=False)
            csvFile = cf.export()
            filename = filename % cf.name
        elif objType == 'cs':
            cs = mmodels.CurveSet.get(id=int(objId), deleted=False)
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
def browseFileSet(request, user):
    files = mmodels.FileSet.all()
    context = {
        'user': user,
        'list_header': 'Displaying uploaded files sets:',
        'list_to_disp': files,
        'action1': "showFileSet",
        'action2': "deleteFileSet",
        'action2_text': ' (delete) ',
        'whenEmpty': ''.join([
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
def browseCurveFile(request, user):
    files = mmodels.CurveFile.all()
    context = {
        'user': user,
        'list_header': 'Displaying Uploaded files:',
        'list_to_disp': files,
        'action1': "showCurveFile",
        'action2': "deleteCurveFile",
        'action2_text': ' (delete) ',
        'whenEmpty': ''.join([
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
def browseAnalysis(request, user):
    anals = mmodels.Analysis.all()
    context = {
        'user': user,
        'list_header': 'Displaying Analysis:',
        'list_to_disp': anals,
        'action1': "showAnalysis",
        'action2': "deleteAnalysis",
        'action2_text': ' (delete) ',
        'whenEmpty': ''.join([
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
def browseCurveSet(request, user):
    csets = mmodels.CurveSet.all()
    context = {
        'user': user,
        'list_header': 'Displaying CurveSets:',
        'list_to_disp': csets,
        'action1': 'showCurveSet',
        'action2': 'deleteCurveSet',
        'action2_text': ' (delete) ',
        'whenEmpty': ''.join([
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
        cfile = mmodels.CurveFile.get(id=file_id)
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
            cd = mmodels.CurveData.get(id=delId)
            delete_fun = mmodels.CurveFile.get(id=objId).curveSet.curvesData.remove
        except ObjectDoesNotExist:
            print('CF: obj does not exists')
            raise
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
            cd = mmodels.CurveData.get(id=delId)
            delete_fun = mmodels.CurveSet.get(id=objId).curvesData.remove
        except ObjectDoesNotExist:
            print('CS: obj does not exists')
            raise
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
        'formHTML': form.drawByHand(request),
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

    form_data = {'model': an, 'label_name': 'Analysis name'}
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
    plotScr, plotDiv = generate_plot(
        request=request,
        user=user,
        plot_type='curveset',
        value_id=an.curveSet.id
    )
    if mm.methodCanBeApplied():
        applyClass = '_voltJS_applyModel _voltJS_model@' + str(an.id)
    else:
        applyClass = '_disabled'

    context = {
        'scripts': plotScr,
        'mainPlot': plotDiv,
        'head': info.get('head', ''),
        'user': user,
        'analysis': an,
        'disp_name_edit': form_ret['html'],
        'text': info.get('body', ''),
        'exportData': get_redirect_class(
            reverse('export', kwargs={
                'objType': 'an',
                'objId': an.id,
            })
        ),
        'applyModel': applyClass
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

    form_data = {'model': fs, 'label_name': 'FileSet name'}
    edit_name_form = form_helper(
        user=user,
        request=request,
        formClass=mforms.EditName,
        submitName='anEditName',
        submitText='Save',
        formExtraData=form_data
    )

    plotScr, plotDiv = generate_plot(
        request=request,
        user=user,
        plot_type='fileset',
        value_id=fs.id
    )

    context = {
        'scripts': plotScr,  # + formAnalyze.getJS(request) + formProcess.getJS(request),
        'mainPlot': plotDiv,
        'user': user,
        'disp_name_edit': edit_name_form['html'],
        'fileset': fs,
        'exportFS': get_redirect_class(
            reverse('export', kwargs={
                'objType': 'fs',
                'objId': fs.id,
            })
        ),
        'cloneCS': get_redirect_class(
            reverse('cloneFileSet', kwargs={
                'toCloneId': fs.id
            })
        ),
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

    form_data = {'model': cs, 'label_name': 'CurveSet name'}
    edit_name_form = form_helper(
        user=user,
        request=request,
        formClass=mforms.EditName,
        submitName='anEditName',
        submitText='Save',
        formExtraData=form_data
    )

    plotScr, plotDiv = generate_plot(
        request=request,
        user=user,
        plot_type='curveset',
        value_id=cs.id
    )

    filesUsed = set()
    for cd in cs.curvesData.all():
        filesUsed.add(cd.curve.curveFile)

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

    context = {
        'scripts': plotScr + formAnalyze.getJS(request) + formProcess.getJS(request),
        'mainPlot': plotDiv,
        'user': user,
        'disp_name_edit': edit_name_form['html'],
        'curveset': cs,
        'filesUsed': filesUsed,
        'at': at_disp,
        'formProcess': formProcess,
        'formAnalyze': formAnalyze,
        'exportCS': get_redirect_class(
            reverse('export', kwargs={
                'objType': 'cs',
                'objId': cs.id,
            })
        ),
        'undoCS': get_redirect_class(
            reverse('undoCurveSet', kwargs={
                'curveset_id': cs.id,
            })
        ),
        'cloneCS': get_redirect_class(
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
    toCloneCS = mmodels.CurveFile.get(id=int(toCloneId)).curveSet
    newcs = toCloneCS.getNewCurveSet()
    add_notification(request, 'File copied as a new CurveSet. Redirecting to the new CurveSet.')
    return HttpResponseRedirect(newcs.getUrl())


@redirect_on_voltpyexceptions
@with_user
def upload(request, user):
    context = {
        'user': user,
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
        cf = mmodels.CurveFile.get(id=file_id, deleted=False)
    except ObjectDoesNotExist:
        raise VoltPyNotAllowed(user)

    form_data = {'model': cf, 'label_name': 'System name'}
    edit_name_form = form_helper(
        user=user,
        request=request,
        formClass=mforms.EditName,
        submitName='anEditName',
        submitText='Save',
        formExtraData=form_data
    )

    import manager.analytesTable as at
    plotScr, plotDiv = generate_plot(
        request=request,
        user=user,
        plot_type='file',
        value_id=cf.id
    )

    at_disp = at.analytesTable(cf, objType='cf')

    context = {
        'scripts': plotScr,
        'mainPlot': plotDiv,
        'user': user,
        'curvefile': cf,
        'disp_name_edit': edit_name_form['html'],
        'at': at_disp,
        'exportCF': get_redirect_class(
            reverse('export', kwargs={
                'objType': 'cf',
                'objId': cf.id,
            })
        ),
        'cloneCS': get_redirect_class(
            reverse('cloneCurveFile', kwargs={
                'toCloneId': cf.curveSet.id,
            })
        ),
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
            cf = mmodels.CurveFile.get(id=objId)
        except ObjectDoesNotExist:
            raise VoltPyNotAllowed
        cs = cf.curveSet

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
    plotScr, plotDiv = generate_plot(
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
        'mainPlot': plotDiv,
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
    return
