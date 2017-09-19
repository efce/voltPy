from django.shortcuts import render
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.template import loader
from django.views.decorators.cache import never_cache
from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist
import json
import manager.models as mmodels
from manager.forms import * 
from manager.plotmanager import *
from manager.methodmanager import *

def with_user(fun):
    def wrap(*args, **kwargs):
        user_id = kwargs.pop('user_id', None)
        try:
            user_id = int(user_id)
        except (TypeError, ValueError):
            raise PermissionError('No user')
        try:
            user = mmodels.User.objects.get(id=user_id)
        except ObjectDoesNotExist:
            raise PermissionError('No user')
        kwargs['user'] = user
        return fun(*args, **kwargs)
    return wrap

def indexNoUser(request):
    template = loader.get_template('manager/index.html')
    return HttpResponse(template.render({'user' : None }, request))

@with_user
def index(request, user):
    template = loader.get_template('manager/index.html')
    return HttpResponse(template.render({ 'user': user }, request))

def login(request):
    user_id = 1
    try:
        user = User.objects.get(id=user_id)
    except ObjectDoesNotExist:
        user = User(name="Użytkownik numer %i" % user_id)
        user.save()
    return HttpResponseRedirect(reverse('index', args=[ user.id ]))

def logout(request):
    return HttpResponseRedirect(reverse('indexNoUser'))

@with_user
def browseCurveFile(request, user):
    files = CurveFile.objects.filter(owner=user, deleted=False)

    template = loader.get_template('manager/browse.html')
    context = {
        'scripts': PlotManager.required_scripts,
        'browse_by' : 'files',
        'user' : user,
        'disp' : files,
        'action1': "editCurveFile",
        'action2': "deleteCurveFile",
        'action2_text': '(delete)',
        'whenEmpty' : "You have no files uploaded. <a href=" +\
                        reverse('upload', args=[user.id]) + ">Upload one</a>."
    }
    return HttpResponse(template.render(context, request))

@with_user
def browseAnalysis(request, user):
    anals = Analysis.objects.filter(owner=user, deleted=False)
    template = loader.get_template('manager/browse.html')
    context = {
        'scripts': PlotManager.required_scripts,
        'browse_by' : 'Analysis',
        'user' : user,
        'disp' : anals,
        'action1': "showAnalysis",
        'action2': "deleteAnalysis",
        'action2_text': '(delete)',
        'whenEmpty' : "Analysis can only be performed on the CurveSet" 
    }
    return HttpResponse(template.render(context, request))

@with_user
def browseCurveSet(request, user):
    csets = CurveSet.objects.filter(owner=user, deleted=False)

    if ( __debug__ ):
        print(csets)
    template = loader.get_template('manager/browse.html')
    context = {
        'scripts': PlotManager.required_scripts,
        'browse_by' : 'Curve Set',
        'user' : user,
        'disp' : csets,
        'action1': 'editCurveSet',
        'action2': 'deleteCurveSet',
        'action2_text': ' (delete) ',
        'whenEmpty' : "You have no curve sets. <a href=" +\
                        reverse('createCurveSet', args=[user.id]) + ">Prepare one</a>."
    }
    return HttpResponse(template.render(context, request))

def deleteGeneric(request, user, item):
    if item == None:
        return HttpResponseRedirect(
            reverse('index', args=[user.id])
        )

    itemclass = str(item.__class__.__name__)
    try:
        if not item.canBeUpdatedBy(user):
            raise PermissionError("Not allowed")
    except PermissionError: #TODO: let it go
        if ( __debug__ ):
            print("Not allowed to edit %s by %s" % (item,user))
        return HttpResponseRedirect(
            reverse('browse'+itemclass, args=[user.id])
        )
    if request.method == 'POST':
        form = DeleteForm(item, request.POST)
        if form.is_valid():
            a = form.process(user, item)
            if a:
                return HttpResponseRedirect(
                    reverse('browse'+itemclass, args=[user.id])
                )
    else:
        form = DeleteForm(item)

    context = { 
        'scripts': PlotManager.required_scripts,
        'form': form,
        'item': item,
        'user': user
    }
    return render(request, 'manager/deleteGeneric.html', context)

@with_user
def deleteCurveFile(request, user, file_id):
    try:
        cfile = CurveFile.objects.get(id=file_id)
    except ObjectDoesNotExist:
        cfile = None
    return deleteGeneric(request, user, cfile)

@with_user
def deleteCurve(request, user, curve_id):
    try:
        c = Curve.objects.get(id=curve_id)
    except ObjectDoesNotExist:
        c=None
    return deleteGeneric(request, user, c)

@with_user
def deleteAnalysis(request, user, analysis_id):
    try:
        a = Analysis.objects.get(id=analysis_id)
    except ObjectDoesNotExist:
        a=None
    return deleteGeneric(request, user, a)

@with_user
def deleteCurveSet(request, user, curveset_id):
    try:
        a = CurveSet.objects.get(id=curveset_id)
        if ( a.locked ):
            pass
            #TODO: cannot be modified.
    except ObjectDoesNotExist:
        a=None
    return deleteGeneric(request, user, a)

@with_user
def createCurveSet(request, user):
    if request.method == 'POST':
        form = SelectCurvesForCurveSetForm(user, request.POST)
        if form.is_valid():
            if ( form.process(user) == True ):
                cs_id = form.curvesetid
                if cs_id and cs_id > -1:
                    return HttpResponseRedirect(
                            reverse('editCurveSet', args=[user.id, cs_id])
                    )
    else:
        form = SelectCurvesForCurveSetForm(user)

    context = {
        'scripts': PlotManager.required_scripts,
        'form': form, 
        'user': user
    }
    return render(request, 'manager/createCurveSet.html', context)


@with_user
def showAnalysis(request, user, analysis_id):
    try:
        an = Analysis.objects.get(id=analysis_id)
    except ObjectDoesNotExist:
        an = None

    if not an.canBeReadBy(user):
        raise PermissionError('Not allowed')

    if an.completed == False:
        return HttpResponseRedirect(reverse('analyze', args=[user.id, an.id]))

    mm = MethodManager(user=user, analysis_id=analysis_id)
    template = loader.get_template('manager/showAnalysis.html')
    info = mm.getInfo(request=request, user=user)
    plotScr, plotDiv = generatePlot(
        request=request, 
        user=user, 
        plot_type='curveset',
        value_id=an.curveSet.id
    )
    context = {
        'scripts': PlotManager.required_scripts + plotScr,
        'mainPlot': plotDiv,
        'head': info.get('head',''),
        'user' : user,
        'analysis': an,
        'plot_width' : PlotManager.plot_width,
        'plot_height' : PlotManager.plot_height,
        'text': info.get('body','')
    }
    return HttpResponse(template.render(context, request))

@with_user
def showProcessed(request, user, processing_id):
    try:
        cf = Processing.objects.get(id=processing_id, owner=user)
    except ObjectDoesNotExist:
        cf = None

    template = loader.get_template('manager/showAnalysis.html')
    context = {
        'scripts': PlotManager.required_scripts,
        'user' : user,
        'processing': processing_id,
        'plot_width' : PlotManager.plot_width,
        'plot_height' : PlotManager.plot_height,
    }
    return HttpResponse(template.render(context, request))

@with_user
def showCurveSet(request, user, curveset_id):
    try:
        cs = CurveSet.objects.get(id=curveset_id)
    except ObjectDoesNotExist:
        cs = None

    if not cs.canBeReadBy(user):
        raise PermissionError('Not allowed')

    template = loader.get_template('manager/showCurveSet.html')
    plotScr, plotDiv = generatePlot(
        request=request, 
        user=user, 
        plot_type ='curveset',
        value_id = cs.id
    )
    context = {
        'scripts': PlotManager.required_scripts + plotScr,
        'mainPlot' : plotDiv,
        'user' : user,
        'curveset_id': curveset_id,
        'plot_width' : PlotManager.plot_width,
        'plot_height' : PlotManager.plot_height,
    }
    return HttpResponse(template.render(context, request))

@with_user
def editAnalysis(request, user, analysis_id):
    pass

@with_user
def editCurveSet(request,user,curveset_id):
    try:
        cs=CurveSet.objects.get(id=curveset_id)
    except ObjectDoesNotExist:
        raise 404

    if not cs.canBeUpdatedBy(user):
        raise PermissionError('Not allowed')

    if ( cs.locked ):
        #show that is is locked
        pass

    mm = MethodManager(user=user, curveset_id=curveset_id)

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
            formProc = mm.getProcessingSelectionForm()

        if ( 'submitFormAnalyte' in request.POST ):
            formAnalyte = AddAnalytesForm(user, "CurveSet", curveset_id, request.POST)
            if formAnalyte.is_valid():
                if ( formAnalyte.process(user) == True ):
                    return HttpResponseRedirect(
                        reverse('showCurveSet', args=[user.id, curveset_id])
                    )
        else:
            formAnalyte = AddAnalytesForm(user, "CurveSet", curveset_id)

    else:
        formAnalyte = AddAnalytesForm(user, "CurveSet", curveset_id)
        formGenerate = mm.getAnalysisSelectionForm()
        formProc = mm.getProcessingSelectionForm()

    try:
        cs = CurveSet.objects.get(id=curveset_id)
        if not cs.canBeReadBy(user):
            raise PermissionError('Not allowed')
    except PermissionError:
        raise 404

    cal_disp = ""
    plotScr, plotDiv = generatePlot(
        request=request, 
        user=user, 
        plot_type='curveset',
        value_id=cs.id
    )
    context = { 
        'scripts': PlotManager.required_scripts + plotScr,
        'mainPlot' : plotDiv,
        'formAnalyte': formAnalyte, 
        'startAnalyze' : formGenerate,
        'startProcessing' : formProc,
        'user' : user, 
        'curveset_id' : curveset_id, 
        'plot_width' : PlotManager.plot_width,
        'plot_height' : PlotManager.plot_height,
        'cal_disp': cal_disp
    }
    return render(request, 'manager/editCurveSet.html', context)

@with_user
def upload(request, user):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            if ( form.process(user, request) == True ):
                file_id = form.file_id
                return HttpResponseRedirect(
                    reverse('editCurveFile', args=[user.id, file_id])
                )
    else:
        form = UploadFileForm()

    context = {
        'scripts': PlotManager.required_scripts,
        'form': form, 
        'user': user
    }
    return render(request, 'manager/uploadFile.html', context)


@with_user
def editCurveFile(request, user, file_id,):
    if request.method == 'POST':
        form = AddAnalytesForm(user, "File", file_id, request.POST)
        if form.is_valid():
            if ( form.process(user) == True ):
                return HttpResponseRedirect(
                    reverse('browseCurveFile', args=[user.id])
                )
    else:
        form = AddAnalytesForm(user, "File", file_id)
    plotScr, plotDiv = generatePlot(
        request=request, 
        user=user, 
        plot_type='file',
        value_id=file_id
    )
    context = { 
        'scripts': PlotManager.required_scripts + plotScr,
        'mainPlot' : plotDiv,
        'user' : user, 
        'file_id' : file_id,
        'form': form,
        'plot_width' : PlotManager.plot_width,
        'plot_height' : PlotManager.plot_height
    }
    return render(request, 'manager/editFile.html', context)

@with_user
def showCurveFile(request, user, file_id):
    try:
        cf = CurveFile.objects.get(id=file_id, deleted=False)
    except ObjectDoesNotExist:
        cf = None

    if not cf.canBeReadBy(user):
        raise PermissionError('Not allowed')

    if ( __debug__): 
        print(cf)
    template = loader.get_template('manager/showFile.html')
    plotScr, plotDiv = generatePlot(
        request=request, 
        user=user, 
        plot_type='file',
        value_id=cf.id
    )
    context = { 
        'scripts': PlotManager.required_scripts + plotScr,
        'mainPlot' : plotDiv,
        'user' : user,
        'curvefile_id': curvefile_id,
        'plot_width' : PlotManager.plot_width,
        'plot_height' : PlotManager.plot_height,
        'form' : form
    }
    return HttpResponse(template.render(context, request))

@with_user
def analyze(request, user, analysis_id):
    mm = MethodManager(user=user, analysis_id=analysis_id)
    mm.process(request=request, user=user)
    return mm.getContent(request=request, user=user) 

@with_user
def process(request, user, processing_id):
    mm = MethodManager(user=user, processing_id=processing_id)
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
        mm = MethodManager(user=user, **kwrg)
        mm.process(request=request, user=user)
        ret = mm.getJSON(user=user)
    elif (request.POST.get('query') == 'plotmanager' ): 
        pm = PlotManager()
        ret = pm.plotInteraction(request=request, user=user)
    else:
        raise NameError('Unknown query type')

    return HttpResponse(
        json.dumps(ret),
        'type=application/json'
    )

#@never_cache
def generatePlot(request, user, plot_type, value_id, **kwargs):
    allowedTypes = [
        'file',
        'analysis',
        'curveset',
        'curves'
    ]
    if not ( plot_type in allowedTypes ):
        return
    vtype = kwargs.get('vtype', plot_type)
    vid = kwargs.get('vid', value_id)
    addTo = kwargs.get('add', None)

    pm = PlotManager()
    data=[]
    if (plot_type == 'file' ):
        data=pm.fileHelper(user, value_id)
        pm.xlabel = pm.xLabelHelper(user)
        pm.include_x_switch = True
    elif (plot_type == 'curveset'):
        data=pm.curveSetHelper(user, value_id)
        pm.xlabel = pm.xLabelHelper(user)
        pm.include_x_switch = True
    elif (plot_type == 'analysis'):
        data=pm.analysisHelper(user, value_id)
        xlabel = pm.xLabelHelper(user)
        pm.include_x_switch = False
    elif (plot_type == 'curves'):
        data=pm.curvesHelper(user, value_id)
        pm.xlabel = pm.xLabelHelper(user)
        pm.include_x_switch = True


    pm.ylabel = 'i / µA'
    pm.setInteraction(kwargs.get('interactionName', 'none'))

    for d in data:
        pm.add(**d)

    if addTo:
        for a in addTo:
            pm.add(**a)

    return pm.getEmbeded(request, user, vtype, vid) 
