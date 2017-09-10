from django.shortcuts import render
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.template import loader
from django.views.decorators.cache import never_cache
from django.core.urlresolvers import reverse
import json
from .models import *
from .forms import *
from .plotmanager import *
from .methodmanager import *


def indexNoUser(request):
    template = loader.get_template('manager/index.html')
    return HttpResponse(template.render({'user' : None }, request))


def index(request, user_id):
    template = loader.get_template('manager/index.html')
    try:
        user = User.objects.get(id=user_id)
    except:
        user=None
    return HttpResponse(template.render({ 'user': user }, request))


def login(request):
    user_id = 1
    try:
        user = User.objects.get(id=user_id)
    except:
        user = User(name="Użytkownik numer %i" % user_id)
        user.save()
    return HttpResponseRedirect(reverse('index', args=[ user.id ]))


def logout(request):
    return HttpResponseRedirect(reverse('indexNoUser'))


def browseCurveFile(request, user_id):
    try:
        user = User.objects.get(id=user_id)
    except:
        user=None

    try:
        files = CurveFile.objects.filter(owner=user, deleted=False)
    except:
        files = None

    template = loader.get_template('manager/browse.html')
    context = {
            'scripts': PlotManager.required_scripts,
            'browse_by' : 'files',
            'user' : user,
            'disp' : files,
            'action1': "editCurveFile",
            'action2': "deleteCurveFile",
            'action2_text': '(delete)',
            'whenEmpty' : "You have no files uploaded. <a href=" + 
                                reverse('upload', args=[user_id]) + ">Upload one</a>."
    }
    return HttpResponse(template.render(context, request))


def browseAnalysis(request, user_id):
    try:
        user = User.objects.get(id=user_id)
    except:
        user=None

    try:
        files = Analysis.objects.filter(owner=user, deleted=False)
    except:
        files = None

    template = loader.get_template('manager/browse.html')
    context = {
            'scripts': PlotManager.required_scripts,
            'browse_by' : 'Analysis',
            'user' : user,
            'disp' : files,
            'action1': "showAnalysis",
            'action2': "deleteAnalysis",
            'action2_text': '(delete)',
            'whenEmpty' : "Analysis can only be performed on the CurveSet" 
    }
    return HttpResponse(template.render(context, request))


def browseCurveSet(request, user_id):
    try:
        user = User.objects.get(id=user_id)
    except:
        user=None

    try:
        csets = CurveSet.objects.filter(owner=user_id, deleted=False)
    except:
        csets = None

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
            'whenEmpty' : "You have no curve sets. <a href=" +
                                reverse('createCurveSet', args=[user_id]) + ">Prepare one</a>."
    }
    return HttpResponse(template.render(context, request))


def deleteGeneric(request, user_id, item):
    if item == None:
        return HttpResponseRedirect(
                    reverse('index', args=[user_id])
                )

    try:
        user = User.objects.get(id=user_id)
    except:
        user=None
    itemclass = str(item.__class__.__name__)
    try:
        if not item.canBeUpdatedBy(user):
            raise PermissionError("Not allowed")
    except:
        if ( __debug__ ):
            print("Not allowed to edit %s by %s" % (item,user))
        return HttpResponseRedirect(
                    reverse('browse'+itemclass, args=[user_id])
                )
    if request.method == 'POST':
        form = DeleteForm(item, request.POST)
        if form.is_valid():
            a = form.process(user, item)
            if a:
                return HttpResponseRedirect(
                        reverse('browse'+itemclass, args=[user_id])
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


def deleteCurveFile(request, user_id, file_id):
    try:
        cfile = CurveFile.objects.get(id=file_id)
    except:
        cfile = None
    return deleteGeneric(request, user_id, cfile)


def deleteCurve(request, user_id, curve_id):
    try:
        c = Curve.objects.get(id=curve_id)
    except:
        c=None
    return deleteGeneric(request, user_id, c)


def deleteAnalysis(request, user_id, analysis_id):
    try:
        a = Analysis.objects.get(id=analysis_id)
    except:
        a=None
    return deleteGeneric(request, user_id, a)


def deleteCurveSet(request, user_id, curveset_id):
    try:
        a = CurveSet.objects.get(id=curveset_id)
        if ( a.locked ):
            pass
            #TODO: cannot be modified.
    except:
        a=None
    return deleteGeneric(request, user_id, a)


def createCurveSet(request, user_id):
    try:
        user = User.objects.get(id=user_id)
    except:
        user=None

    if request.method == 'POST':
        form = SelectCurvesForCurveSetForm(user, request.POST)
        if form.is_valid():
            if ( form.process(user) == True ):
                cs_id = form.curvesetid
                if cs_id and cs_id > -1:
                    return HttpResponseRedirect(reverse('editCurveSet', args=[user_id, cs_id]))
    else:
        form = SelectCurvesForCurveSetForm(user)

    context = {
            'scripts': PlotManager.required_scripts,
            'form': form, 
            'user': user
            }
    return render(request, 'manager/createCurveSet.html', context)


def showAnalysis(request, user_id, analysis_id):
    try:
        user = User.objects.get(id=user_id)
    except:
        user=None

    try:
        an = Analysis.objects.get(id=analysis_id)
    except:
        an = None

    if not an.canBeReadBy(user):
        raise 3

    if an.completed == False:
        return HttpResponseRedirect(reverse('analyze', args=[user.id, an.id]))

    dataop = MethodManager(analysis=analysis_id)
    template = loader.get_template('manager/showAnalysis.html')
    info = dataop.getInfo(user)
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


def showProcessed(request, user_id, processing_id):
    try:
        user = User.objects.get(id=user_id)
    except:
        user=None

    try:
        cf = Processing.objects.get(id=processing_id, owner=user)
    except:
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


def showCurveSet(request, user_id, curveset_id):
    try:
        user = User.objects.get(id=user_id)
    except:
        user=None

    try:
        cs = CurveSet.objects.get(id=curveset_id)
    except:
        cs = None

    if not cs.canBeReadBy(user):
        raise 3

    template = loader.get_template('manager/showCurveSet.html')
    plotScr, plotDiv = generatePlot(
            request=request, 
            user=user, 
            plot_type ='curveset',
            value_id = cs.id)
    context = {
            'scripts': PlotManager.required_scripts + plotScr,
            'mainPlot' : plotDiv,
            'user' : user,
            'curveset_id': curveset_id,
            'plot_width' : PlotManager.plot_width,
            'plot_height' : PlotManager.plot_height,
    }
    return HttpResponse(template.render(context, request))



def editAnalysis(request, user_id, analysis_id):
    pass



def editCurveSet(request,user_id,curveset_id):
    try:
        user = User.objects.get(id=user_id)
    except:
        user=None

    try:
        cs=CurveSet.objects.get(id=curveset_id)
    except:
        raise 404

    if not cs.canBeUpdatedBy(user):
        raise 3

    if ( cs.locked ):
        #show that is is locked
        pass

    dataop = MethodManager(curveset=curveset_id)

    if request.method == 'POST':
        if ( 'startAnalyze' in request.POST ):
            formGenerate = dataop.getAnalysisSelectionForm(request.POST)
            if ( formGenerate.is_valid() ):
                analyzeid = formGenerate.process(user,cs)
                return HttpResponseRedirect(reverse('analyze', args=[user_id, analyzeid]))
        else:
            formGenerate = dataop.getAnalysisSelectionForm()

        if ( not cs.locked
        and 'startProcessing' in request.POST ):
            formProc = dataop.getProcessingSelectionForm(request.POST)
            if ( formProc.is_valid() ):
                procid = formProc.process(user,cs)
                return HttpResponseRedirect(reverse('process', args=[user_id, procid]))
        else:
            formProc = dataop.getProcessingSelectionForm()

        if ( 'submitFormAnalyte' in request.POST ):
            formAnalyte = AddAnalytesForm(user, "CurveSet", curveset_id, request.POST)
            if formAnalyte.is_valid():
                if ( formAnalyte.process(user) == True ):
                    return HttpResponseRedirect(reverse('showCurveSet', args=[user_id, curveset_id]))
        else:
            formAnalyte = AddAnalytesForm(user, "CurveSet", curveset_id)

    else:
        formAnalyte = AddAnalytesForm(user, "CurveSet", curveset_id)
        formGenerate = dataop.getAnalysisSelectionForm()
        formProc = dataop.getProcessingSelectionForm()

    try:
        cs = CurveSet.objects.get(id=curveset_id)
        if not cs.canBeReadBy(user):
            raise 3
    except:
        raise 404

    cal_disp = ""
    plotScr, plotDiv = generatePlot(
            request=request, 
            user=user, 
            plot_type='curveset',
            value_id=cs.id)
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


def upload(request, user_id):
    try:
        user = User.objects.get(id=user_id)
    except:
        user=None

    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            if ( form.process(user, request) == True ):
                file_id = form.file_id
                return HttpResponseRedirect(reverse('editCurveFile', args=[user_id, file_id]))
    else:
        form = UploadFileForm()

    context = {
            'scripts': PlotManager.required_scripts,
            'form': form, 
            'user': user
            }
    return render(request, 'manager/uploadFile.html', context)


def editCurveFile(request, user_id, file_id,):
    try:
        user = User.objects.get(id=user_id)
    except:
        user=None

    if request.method == 'POST':
        form = AddAnalytesForm(user, "File", file_id, request.POST)
        if form.is_valid():
            if ( form.process(user) == True ):
                return HttpResponseRedirect(reverse('browseCurveFile', args=[user_id]))
    else:
        form = AddAnalytesForm(user, "File", file_id)
    plotScr, plotDiv = generatePlot(
            request=request, 
            user=user, 
            plot_type='file',
            value_id=file_id)
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


def showCurveFile(request, user_id, file_id):
    try:
        user = User.objects.get(id=user_id)
    except:
        user=None

    try:
        cf = CurveFile.objects.get(id=file_id, deleted=False)
    except:
        cf = None

    if not cf.canBeReadBy(user):
        raise 3

    if ( __debug__): 
        print(cf)
    template = loader.get_template('manager/showFile.html')
    plotScr, plotDiv = generatePlot(
            request=request, 
            user=user, 
            plot_type='file',
            value_id=cf.id)
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


def processCurveFile(request, user_id, file_id):
    #create curve set from file and call process curveset#
    pass

def processCurveSet(request, user_id, file_id):
    pass

def analyze(request, user_id, analysis_id):
    try:
        user = User.objects.get(id=user_id)
    except:
        user=None
    dataop = MethodManager(analysis = analysis_id)
    dataop.process(user, request)
    return dataop.getContent(user) 


def process(request, user_id, processing_id):
    try:
        user = User.objects.get(id=user_id)
    except:
        user=None
    dataop = MethodManager(processing = processing_id)
    dataop.process(user, request)
    return dataop.getContent(user) 


def plotInteraction(request, user_id):
    try:
        user = User.objects.get(id=user_id)
    except:
        user=None

    if request.method != 'POST' or not request.POST.get('query', None):
        return HttpResponse('Error')
    
    vtype =  request.POST.get('vtype', '')
    vid = int(request.POST.get('vid', -1))
    kwrg = {
            vtype: vid
    }
    try:
        mm = MethodManager(**kwrg)
    except:
        mm = None
    pm = PlotManager()
    pm.active_class = mm
    return HttpResponse(
            json.dumps(pm.plotInteraction(request=request, user=user)),
            'type=application/json'
    )
        

#@never_cache
def generatePlot(request, user, plot_type, value_id):
    allowedTypes = [
        'file',
        'analysis',
        'curveset',
        'curves'
    ]
    if not ( plot_type in allowedTypes ):
        return

    pm = PlotManager()
    #pm.processJSON(request, user)
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

    for d in data:
        pm.add(**d)
        """
            x=d.get('x',[]), 
            y=d.get('y', []),
            name=d.get('name',''),
            color=d.get('color','blue'),
            isLine=d.get('isLine', True)
        )
        """

    return pm.getEmbeded(request, user, plot_type, value_id) 
