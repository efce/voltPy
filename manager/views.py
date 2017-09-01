from django.shortcuts import render
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.template import loader
from django.views.decorators.cache import never_cache
from django.core.urlresolvers import reverse
from .models import *
from .forms import *
from .plotmaker import PlotMaker
from .data_operation import DataOperation


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
            'browse_by' : 'Analysis',
            'user' : user,
            'disp' : files,
            'action1': "showAnalysis",
            'action2': "deleteAnalysis",
            'action2_text': '(delete)',
            'whenEmpty' : "Analysis can only be performed on the CurveSet" 
    }
    return HttpResponse(template.render(context, request))


def editAnalysis(request, user_id, analysis_id):
    pass


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
        an = Analysis.objects.get(id=analysis_id, owner=user)
    except:
        an = None

    if an.completed == False:
        return HttpResponseRedirect(reverse('analyze', args=[user.id, an.id]))


    dataop = DataOperation(analysis=analysis_id)
    template = loader.get_template('manager/showAnalysis.html')
    info = dataop.getInfo()
    context = {
            'head': info.get('head',''),
            'user' : user,
            'analysis': an,
            'plot_width' : PlotMaker.plot_width,
            'plot_height' : PlotMaker.plot_height,
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
            'user' : user,
            'processing': processing_id,
            'plot_width' : PlotMaker.plot_width,
            'plot_height' : PlotMaker.plot_height,
    }
    return HttpResponse(template.render(context, request))


def showCurveSet(request, user_id, curveset_id):
    try:
        user = User.objects.get(id=user_id)
    except:
        user=None

    try:
        cf = CurveSet.objects.get(id=curveset_id)
    except:
        cf = None

    template = loader.get_template('manager/showCurveSet.html')
    context = {
            'user' : user,
            'curveset_id': curveset_id,
            'plot_width' : PlotMaker.plot_width,
            'plot_height' : PlotMaker.plot_height,
    }
    return HttpResponse(template.render(context, request))


def editCurveSet(request,user_id,curveset_id):
    try:
        user = User.objects.get(id=user_id)
    except:
        user=None

    dataop = DataOperation(curveset=curveset_id)

    if request.method == 'POST':
        if ( 'startAnalyze' in request.POST ):
            formGenerate = dataop.getAnalysisSelectForm(request.POST)
            if ( formGenerate.is_valid() ):
                analyzeid = formGenerate.process(user)
                return HttpResponseRedirect(reverse('analyze', args=[user_id, analyzeid]))
        else:
            formGenerate = dataop.getAnalysisSelectForm()

        if ( 'startProcessing' in request.POST ):
            formProc = dataop.getProcessingSelectForm(request.POST)
            if ( formProc.is_valid() ):
                procid = formProc.process(user)
                return HttpResponseRedirect(reverse('process', args=[user_id, procid]))
        else:
            formProc = dataop.getProcessingSelectForm()

        if ( 'submitFormAnalyte' in request.POST ):
            formAnalyte = AddAnalytesForm(user, "CurveSet", curveset_id, request.POST)
            if formAnalyte.is_valid():
                if ( formAnalyte.process(user) == True ):
                    return HttpResponseRedirect(reverse('showCurveSet', args=[user_id, curveset_id]))
        else:
            formAnalyte = AddAnalytesForm(user, "CurveSet", curveset_id)

    else:
        formAnalyte = AddAnalytesForm(user, "CurveSet", curveset_id)
        formGenerate = dataop.getAnalysisSelectForm()
        formProc = dataop.getProcessingSelectForm()

    try:
        cs = CurveSet.objects.get(id=curveset_id)
        if not cs.canBeReadBy(user):
            raise 3
    except:
        raise 404

    cal_disp = ""
    context = { 
            'formAnalyte': formAnalyte, 
            'startAnalyze' : formGenerate,
            'startProcessing' : formProc,
            'user' : user, 
            'curveset_id' : curveset_id, 
            'plot_width' : PlotMaker.plot_width,
            'plot_height' : PlotMaker.plot_height,
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
    context = {
            'user' : user, 
            'file_id' : file_id,
            'form': form,
            'plot_width' : PlotMaker.plot_width,
            'plot_height' : PlotMaker.plot_height
            }
    return render(request, 'manager/editFile.html', context)


def showCurveFile(request, user_id, file_id):
    try:
        user = User.objects.get(id=user_id)
    except:
        user=None

    if request.method == 'POST':
        form = SelectXForm(user_id, request.POST)
        if form.is_valid():
            if ( form.process(user) == True ):
                return HttpResponseRedirect(reverse('showCurveFile', args=[user_id, file_id]))
    else:
        form = SelectXForm(user_id)

    try:
        cf = CurveFile.objects.get(id=file_id, deleted=False)
    except:
        cf = None

    if ( __debug__): 
        print(cf)
    template = loader.get_template('manager/showFile.html')
    context = {
            'user' : user,
            'curvefile_id': curvefile_id,
            'plot_width' : PlotMaker.plot_width,
            'plot_height' : PlotMaker.plot_height,
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
    dataop = DataOperation(analysis = analysis_id)
    dataop.process(user, request)
    return dataop.getContent(user) 


def process(request, user_id, processing_id):
    try:
        user = User.objects.get(id=user_id)
    except:
        user=None
    dataop = DataOperation(processing = processing_id)
    dataop.process(user, request)
    return dataop.getContent(user) 


@never_cache
def generatePlot(request, user_id, plot_type, value_id):
    """
    Allowed types are:
    f - whole file
    a - analysis
    s - curveset
    v - selected curves 
    """
    allowedTypes = {
            'f' : 'File',
            'a' : 'Analysis',
            's' : 'CurveSet',
            'v' : 'Curves'
            }
    if not ( plot_type in allowedTypes ):
        return

    try:
        user = User.objects.get(id=user_id)
    except:
        user=None

    pm = PlotMaker()
    if (plot_type == 'f' ):
        pm.processFile(user, value_id)
    elif (plot_type == 's'):
        pm.processCurveSet(user, value_id)
    elif (plot_type == 'a'):
        pm.processAnalysis(user, value_id)
    elif (plot_type == 'c'):
        pm.processCurves(user, value_id)

    return HttpResponse(
            pm.getPage(), 
            content_type="text/html" 
        )
