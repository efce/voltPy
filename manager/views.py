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
        login(request, user)
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
            fs = mmodels.FileSet.objects.get(id=int(objId), deleted=False)
            if not fs.canBeReadBy(user):
                raise VoltPyNotAllowed()
            csvFile = fs.export()
            filename = filename % fs.name
        elif objType == 'cf':
            cf = mmodels.CurveFile.objects.get(id=int(objId), deleted=False)
            if not cf.canBeReadBy(user):
                raise VoltPyNotAllowed()
            csvFile = cf.export()
            filename = filename % cf.name
        elif objType == 'cs':
            cs = mmodels.CurveSet.objects.get(id=int(objId), deleted=False)
            if not cs.canBeReadBy(user):
                raise VoltPyNotAllowed()
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
    files = mmodels.FileSet.objects.filter(owner=user, deleted=False)
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
    files = mmodels.CurveFile.objects.filter(owner=user, deleted=False)
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
    anals = mmodels.Analysis.objects.filter(owner=user, deleted=False)
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
                url=reverse('browseCurveSet')
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
    files = mmodels.CurveFile.objects.filter(owner=user).only('curveSet')
    csetsFiles = [x['curveSet'] for x in files.all().values('curveSet')]
    csets = mmodels.CurveSet.objects.filter(owner=user, deleted=False).exclude(id__in=csetsFiles)
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
        fs = mmodels.FileSet.objects.get(id=fileset_id)
    except ObjectDoesNotExist:
        fs = None
    return delete_helper(
        request=request,
        user=user,
        item=fs
    )


@redirect_on_voltpyexceptions
@with_user
def deleteCurveFile(request, user, file_id):
    try:
        cfile = mmodels.CurveFile.objects.get(id=file_id)
    except ObjectDoesNotExist:
        cfile = None
    return delete_helper(
        request=request,
        user=user,
        item=cfile
    )


@redirect_on_voltpyexceptions
@with_user
def deleteCurve(request, user, objType, objId, delId):
    if objType == 'cf':
        try:
            cd = mmodels.CurveData.objects.get(id=delId)
            deleteFrom = mmodels.CurveFile.objects.get(id=objId).curveSet
        except ObjectDoesNotExist:
            c = None
        return delete_helper(
            request=request,
            user=user,
            item=cd,
            deleteFrom=deleteFrom,
            onSuccessRedirect=reverse('showCurveFile', args=[deleteFrom.id])
        )
    else:  # curveset
        try:
            cd = mmodels.CurveData.objects.get(id=delId)
            deleteFrom = mmodels.CurveSet.objects.get(id=objId)
        except ObjectDoesNotExist:
            cd = None
        return delete_helper(
            request=request,
            user=user,
            item=cd,
            deleteFrom=deleteFrom,
            onSuccessRedirect=reverse('showCurveSet', args=[deleteFrom.id])
        )


@redirect_on_voltpyexceptions
@with_user
def deleteAnalysis(request, user, analysis_id):
    try:
        a = mmodels.Analysis.objects.get(id=analysis_id)
    except ObjectDoesNotExist:
        a = None
    return delete_helper(
        request=request,
        user=user,
        item=a
    )


@redirect_on_voltpyexceptions
@with_user
def deleteCurveSet(request, user, curveset_id):
    try:
        a = mmodels.CurveSet.objects.get(id=curveset_id)
    except ObjectDoesNotExist:
        a = None
    return delete_helper(
        request=request,
        user=user,
        item=a
    )


@redirect_on_voltpyexceptions
@with_user
def createCurveSet(request, user, toClone=[]):
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
        form = mforms.SelectCurvesForCurveSetForm(user, toClone=toClone)

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
        an = mmodels.Analysis.objects.get(id=analysis_id)
    except ObjectDoesNotExist:
        raise VoltPyNotAllowed(user)

    if not an.canBeReadBy(user):
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
        )
    }
    return voltpy_render(
        request=request,
        template_name='manager/showAnalysis.html',
        context=context
    )


@redirect_on_voltpyexceptions
@with_user
def showProcessed(request, user, processing_id):
    try:
        cf = mmodels.Processing.objects.get(id=processing_id, owner=user)
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
        fs = mmodels.FileSet.objects.get(id=fileset_id)
    except ObjectDoesNotExist:
        raise VoltPyDoesNotExists()

    if not fs.canBeReadBy(user):
        raise VoltPyNotAllowed(user)

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
            reverse('cloneCurveSet', kwargs={
                'toClone_txt': ','.join([str(f.curveSet.id) for f in fs.files.all()])
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
        cs = mmodels.CurveSet.objects.get(id=curveset_id)
    except ObjectDoesNotExist:
        raise VoltPyDoesNotExists()
    if not cs.canBeUpdatedBy(user):
        raise VoltPyNotAllowed(user)

    if request.method == "POST" and request.POST.get('confirm', False):
        confForm = mforms.GenericConfirmForm(request.POST)
        if confForm.confirmed():
            cs.undo()
            add_notification(request, 'Changes undone.')
            return HttpResponseRedirect(reverse('showCurveSet', args=[cs.id]))
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
        cs = mmodels.CurveSet.objects.get(id=curveset_id)
    except ObjectDoesNotExist:
        raise VoltPyDoesNotExists()

    if not cs.canBeReadBy(user):
        raise VoltPyNotAllowed(user)

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
                'toClone_txt': cs.id,
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
def cloneCurveSet(request, user, toClone_txt):
    toClone_ids = [int(x) for x in toClone_txt.split(',')]
    return createCurveSet(request, toClone=toClone_ids)


@redirect_on_voltpyexceptions
@with_user
def editAnalysis(request, user, analysis_id):
    pass


@redirect_on_voltpyexceptions
@with_user
def editCurveSet(request, user, curveset_id):
    try:
        cs = mmodels.CurveSet.objects.get(id=curveset_id)
    except ObjectDoesNotExist:
        raise VoltPyDoesNotExists('Cannot be accessed.')

    if not cs.canBeUpdatedBy(user):
        raise VoltPyNotAllowed(user)

    txt = ''
    if cs.locked:
        txt = "This curveset is used by analysis method and cannot be modified."

    mm = mmm.MethodManager(user=user, curveset_id=curveset_id)

    if request.method == 'POST':
        if 'startAnalyze' in request.POST:
            formGenerate = mm.getAnalysisSelectionForm(request.POST)
            if formGenerate.is_valid():
                analyzeid = formGenerate.process(user, cs)
                return HttpResponseRedirect(reverse('analyze', args=[analyzeid]))
        else:
            formGenerate = mm.getAnalysisSelectionForm()

        if all([
            not cs.locked,
            'startProcessing' in request.POST
        ]):
            formProc = mm.getProcessingSelectionForm(request.POST)
            if formProc.is_valid():
                procid = formProc.process(user, cs)
                return HttpResponseRedirect(reverse('process', args=[procid]))
        else:
            formProc = mm.getProcessingSelectionForm(disabled=cs.locked)

        if 'submitFormAnalyte' in request.POST:
            formAnalyte = mforms.EditAnalytesForm(user, "CurveSet", curveset_id, request.POST)
            if formAnalyte.is_valid():
                if formAnalyte.process(user) is True:
                    return HttpResponseRedirect(
                        reverse('editCurveSet', args=[curveset_id])
                    )
        else:
            formAnalyte = mforms.EditAnalytesForm(user, "CurveSet", curveset_id)

    else:
        formAnalyte = mforms.EditAnalytesForm(user, "CurveSet", curveset_id)
        formGenerate = mm.getAnalysisSelectionForm()
        formProc = mm.getProcessingSelectionForm(disabled=cs.locked)

    try:
        cs = mmodels.CurveSet.objects.get(id=curveset_id)
        if not cs.canBeReadBy(user):
            raise VoltPyNotAllowed(user)
    except ObjectDoesNotExist:
        raise VoltPyNotAllowed(user)

    cal_disp = ""
    plotScr, plotDiv = generate_plot(
        request=request,
        user=user,
        plot_type='curveset',
        value_id=cs.id
    )
    context = {
        'scripts': plotScr + formProc.getJS(request) + formGenerate.getJS(request),
        'mainPlot': plotDiv,
        'formAnalyte': formAnalyte,
        'startAnalyze': formGenerate,
        'startProcessing': formProc,
        'user': user,
        'curveset_id': curveset_id,
        'cal_disp': cal_disp
    }
    return voltpy_render(
        request=request,
        template_name='manager/editCurveSet.html',
        context=context
    )


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
def editCurveFile(request, user, file_id,):
    if request.method == 'POST':
        form = mforms.EditAnalytesForm(user, "File", file_id, request.POST)
        if form.is_valid():
            if form.process(user) is True:
                return HttpResponseRedirect(
                    reverse('browseCurveFile')
                )
    else:
        form = mforms.EditAnalytesForm(user, "File", file_id)
    plotScr, plotDiv = generate_plot(
        request=request,
        user=user,
        plot_type='file',
        value_id=file_id
    )
    context = {
        'scripts': plotScr,
        'mainPlot': plotDiv,
        'user': user,
        'file_id': file_id,
        'form': form,
    }
    return voltpy_render(
        request=request,
        template_name='manager/editFile.html',
        context=context
    )


@redirect_on_voltpyexceptions
@with_user
def showCurveFile(request, user, file_id):
    try:
        cf = mmodels.CurveFile.objects.get(id=file_id, deleted=False)
    except ObjectDoesNotExist:
        raise VoltPyNotAllowed(user)

    if not cf.canBeReadBy(user):
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
            reverse('cloneCurveSet', kwargs={
                'toClone_txt': cf.curveSet.id,
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
def editAnalyte(request, user, objType, objId, analyteId):
    if objType == 'cf':
        try:
            cf = mmodels.CurveFile.objects.get(id=objId, deleted=False)
        except ObjectDoesNotExist:
            raise VoltPyNotAllowed
        if not cf.canBeUpdatedBy(user):
            raise VoltPyNotAllowed
        cs = cf.curveSet

    elif objType == 'cs':
        try:
            cs = mmodels.CurveSet.objects.get(id=objId, deleted=False)
        except ObjectDoesNotExist:
            raise VoltPyNotAllowed
        if not cs.canBeUpdatedBy(user):
            raise VoltPyNotAllowed

    else:
        raise VoltPyNotAllowed

    if request.method == 'POST':
        form = mforms.EditAnalytesForm(user, objType, objId, analyteId, request.POST)
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
        form = mforms.EditAnalytesForm(user, objType, objId, analyteId)

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
            analyte = mmodels.Analyte.objects.get(id=analyteId)
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
