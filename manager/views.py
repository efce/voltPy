from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseRedirect
import json
import manager.models as mmodels
import manager.forms as mforms
from manager import methodmanager as mmm
from manager.exceptions import VoltPyNotAllowed, VoltPyDoesNotExists
from manager.helpers.functions import add_notification
from manager.helpers.functions import delete_generic
from manager.helpers.functions import generate_plot
from manager.helpers.functions import voltpy_render
from manager.helpers.decorators import with_user
from manager.helpers.decorators import redirect_on_voltpyexceptions

@redirect_on_voltpyexceptions
def indexNoUser(request):
    context = {'user': None}
    return voltpy_render(
        request=request, 
        template_name='manager/index.html', 
        context=context
    )

@redirect_on_voltpyexceptions
@with_user
def index(request, user):
    context = {'user': user}
    return voltpy_render(
        request=request, 
        template_name='manager/index.html', 
        context=context
    )

@redirect_on_voltpyexceptions
def login(request):
    #TODO: temp
    user_id = 1
    try:
        user = mmodels.User.objects.get(id=user_id)
    except ObjectDoesNotExist:
        user = mmodels.User(name="Użytkownik numer %i" % user_id)
        user.save()
    add_notification(request, "Logged in successfuly.", 0)
    return HttpResponseRedirect(reverse('index', args=[ user.id ]))

def logout(request):
    add_notification(request, "Logged out successfuly.", 0)
    return HttpResponseRedirect(reverse('indexNoUser'))

@redirect_on_voltpyexceptions
@with_user
def browseCurveFile(request, user):
    files = mmodels.CurveFile.objects.filter(owner=user, deleted=False)
    context = {
        'user' : user,
        'list_header' : 'Displaying Uploaded files:',
        'list_to_disp' : files,
        'action1': "editCurveFile",
        'action2': "deleteCurveFile",
        'action2_text': ' (delete) ',
        'whenEmpty' : ''.join([
                            "You have no files uploaded. ",
                            "<a href='{url}'>Upload one</a>.".format( 
                                url=reverse('upload', args=[user.id])
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
        'user' : user,
        'list_header' : 'Displaying Analysis:',
        'list_to_disp' : anals,
        'action1': "showAnalysis",
        'action2': "deleteAnalysis",
        'action2_text': ' (delete) ',
        'whenEmpty' : ''.join([
                            "Analysis can only be performed on the CurveSet. ",
                            "<a href='{url}'>Choose one</a>.".format( 
                                url=reverse('browseCurveSet', args=[user.id])
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
    csets = mmodels.CurveSet.objects.filter(owner=user, deleted=False)

    if ( __debug__ ):
        print(csets)
    context = {
        'user' : user,
        'list_header' : 'Displaying CurveSets:',
        'list_to_disp' : csets,
        'action1': 'editCurveSet',
        'action2': 'deleteCurveSet',
        'action2_text': ' (delete) ',
        'whenEmpty' : ''.join([
                            "You have no CurveSets. ",
                            "<a href='{url}'>Prepare one</a>.".format( 
                                url=reverse('createCurveSet', args=[user.id])
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
def deleteCurveFile(request, user, file_id):
    try:
        cfile = mmodels.CurveFile.objects.get(id=file_id)
    except ObjectDoesNotExist:
        cfile = None
    return delete_generic(request, user, cfile)

@redirect_on_voltpyexceptions
@with_user
def deleteCurve(request, user, curve_id):
    try:
        c = mmodels.Curve.objects.get(id=curve_id)
    except ObjectDoesNotExist:
        c=None
    return delete_generic(request, user, c)

@redirect_on_voltpyexceptions
@with_user
def deleteAnalysis(request, user, analysis_id):
    try:
        a = mmodels.Analysis.objects.get(id=analysis_id)
    except ObjectDoesNotExist:
        a=None
    return delete_generic(request, user, a)

@redirect_on_voltpyexceptions
@with_user
def deleteCurveSet(request, user, curveset_id):
    try:
        a = mmodels.CurveSet.objects.get(id=curveset_id)
    except ObjectDoesNotExist:
        a=None
    return delete_generic(request, user, a)

@redirect_on_voltpyexceptions
@with_user
def createCurveSet(request, user):
    if request.method == 'POST':
        form = mforms.SelectCurvesForCurveSetForm(user, request.POST)
        if form.is_valid():
            if ( form.process(user) == True ):
                cs_id = form.curvesetid
                if cs_id and cs_id > -1:
                    return HttpResponseRedirect(
                            reverse('editCurveSet', args=[user.id, cs_id])
                    )
    else:
        form = mforms.SelectCurvesForCurveSetForm(user)

    context = {
        'form': form, 
        'user': user
    }
    return voltpy_render(
        request=request, 
        template_name='manager/createCurveSet.html',
        context=context
    )

@redirect_on_voltpyexceptions
@with_user
def showAnalysis(request, user, analysis_id):
    try:
        an = mmodels.Analysis.objects.get(id=analysis_id)
    except ObjectDoesNotExist:
        an = None

    if not an.canBeReadBy(user):
        raise VoltPyNotAllowed(user)

    if an.completed == False:
        return HttpResponseRedirect(reverse('analyze', args=[user.id, an.id]))

    mm = mmm.MethodManager(user=user, analysis_id=analysis_id)
    info = mm.getInfo(request=request, user=user)
    plotScr, plotDiv = generate_plot(
        request=request, 
        user=user, 
        plot_type='curveset',
        value_id=an.curveSet.id
    )
    context = {
        'scripts': plotScr,
        'mainPlot': plotDiv,
        'head': info.get('head',''),
        'user' : user,
        'analysis': an,
        'text': info.get('body','')
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
        'user' : user,
        'processing': processing_id,
    }
    return voltpy_render(
        request=request, 
        template_name='manager/showAnalysis.html',
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

    plotScr, plotDiv = generate_plot(
        request=request, 
        user=user, 
        plot_type ='curveset',
        value_id = cs.id
    )
    context = {
        'scripts': plotScr,
        'mainPlot' : plotDiv,
        'user' : user,
        'curveset_id': curveset_id,
    }
    return voltpy_render(
        request=request, 
        template_name='manager/showCurveSet.html',
        context=context
    )

@redirect_on_voltpyexceptions
@with_user
def editAnalysis(request, user, analysis_id):
    pass

@redirect_on_voltpyexceptions
@with_user
def editCurveSet(request,user,curveset_id):
    try:
        cs = mmodels.CurveSet.objects.get(id=curveset_id)
    except ObjectDoesNotExist:
        raise VoltPyDoesNotExists('Cannot be accessed.')

    if not cs.canBeUpdatedBy(user):
        raise VoltPyNotAllowed(user)

    txt = ''
    if ( cs.locked ):
        txt = "This curveset is used by analysis method and cannot be modified."

    mm = mmm.MethodManager(user=user, curveset_id=curveset_id)

    if request.method == 'POST':
        if ( 'startAnalyze' in request.POST ):
            formGenerate = mm.getAnalysisSelectionForm(request.POST)
            if ( formGenerate.is_valid() ):
                analyzeid = formGenerate.process(user,cs)
                return HttpResponseRedirect(reverse('analyze', args=[user.id, analyzeid]))
        else:
            formGenerate = mm.getAnalysisSelectionForm()

        if ( not cs.locked
        and 'startProcessing' in request.POST ):
            formProc = mm.getProcessingSelectionForm(request.POST)
            if ( formProc.is_valid() ):
                procid = formProc.process(user,cs)
                return HttpResponseRedirect(reverse('process', args=[user.id, procid]))
        else:
            formProc = mm.getProcessingSelectionForm(disabled=cs.locked)

        if ( 'submitFormAnalyte' in request.POST ):
            formAnalyte = mforms.AddAnalytesForm(user, "CurveSet", curveset_id, request.POST)
            if formAnalyte.is_valid():
                if ( formAnalyte.process(user) == True ):
                    return HttpResponseRedirect(
                        reverse('showCurveSet', args=[user.id, curveset_id])
                    )
        else:
            formAnalyte = mforms.AddAnalytesForm(user, "CurveSet", curveset_id)

    else:
        formAnalyte = mforms.AddAnalytesForm(user, "CurveSet", curveset_id)
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
        'mainPlot' : plotDiv,
        'formAnalyte': formAnalyte, 
        'startAnalyze' : formGenerate,
        'startProcessing' : formProc,
        'user' : user, 
        'curveset_id' : curveset_id, 
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
    if request.method == 'POST':
        form = mforms.UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            if (form.process(user, request) == True):
                file_id = form.file_id
                return HttpResponseRedirect(
                    reverse('editCurveFile', args=[user.id, file_id])
                )
    else:
        form = mforms.UploadFileForm()

    context = {
        'form': form, 
        'user': user
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
        form = mforms.AddAnalytesForm(user, "File", file_id, request.POST)
        if form.is_valid():
            if ( form.process(user) == True ):
                return HttpResponseRedirect(
                    reverse('browseCurveFile', args=[user.id])
                )
    else:
        form = mforms.AddAnalytesForm(user, "File", file_id)
    plotScr, plotDiv = generate_plot(
        request=request, 
        user=user, 
        plot_type='file',
        value_id=file_id
    )
    context = { 
        'scripts': plotScr,
        'mainPlot' : plotDiv,
        'user' : user, 
        'file_id' : file_id,
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

    if ( __debug__): 
        print(cf)
    plotScr, plotDiv = generate_plot(
        request=request, 
        user=user, 
        plot_type='file',
        value_id=cf.id
    )
    context = { 
        'scripts': plotScr,
        'mainPlot' : plotDiv,
        'user' : user,
        'curvefile_id': curvefile_id,
        'form' : form
    }
    return voltpy_render(
        request=request, 
        template_name='manager/showFile.html',
        context=context
    )

@redirect_on_voltpyexceptions
@with_user
def analyze(request, user, analysis_id):
    mm = mmm.MethodManager(user=user, analysis_id=analysis_id)
    mm.process(request=request, user=user)
    return mm.getContent(request=request, user=user) 

@redirect_on_voltpyexceptions
@with_user
def process(request, user, processing_id):
    mm = mmm.MethodManager(user=user, processing_id=processing_id)
    mm.process(request=request, user=user)
    return mm.getContent(request=request, user=user) 

@with_user
def plotInteraction(request, user):
    if request.method != 'POST' or not request.POST.get('query', None):
        return HttpResponse('Error')
   
    ret = ''
    if ( request.POST.get('query') == 'methodmanager' ):
        vtype =  request.POST.get('vtype', '')
        vid = int(request.POST.get('vid', -1))
        kwrg = {
            vtype: vid
        }
        mm = mmm.MethodManager(user=user, **kwrg)
        mm.process(request=request, user=user)
        ret = mm.getJSON(user=user)
    elif (request.POST.get('query') == 'plotmanager' ): 
        import manager.plotmanager as mpm
        pm = mpm.PlotManager()
        ret = pm.plotInteraction(request=request, user=user)
    else:
        raise NameError('Unknown query type')

    return HttpResponse(
        json.dumps(ret),
        'type=application/json'
    )
