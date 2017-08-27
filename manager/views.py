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


def browseFiles(request, user_id):
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
            'action1': "editFile",
            'action2': "deleteFile",
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

def deleteAnalysis(request, user_id, analysis_id):
    pass


def editAnalysis(request, user_id, analysis_id):
    pass


def browseCurveSets(request, user_id):
    try:
        user = User.objects.get(id=user_id)
    except:
        user=None

    try:
        csets = CurveSet.objects.filter(owner=user_id)
    except:
        csets = None

    if ( __debug__ ):
        print(csets)
    template = loader.get_template('manager/browse.html')
    context = {
            'browse_by' : 'Curve Set',
            'user' : user,
            'disp' : csets,
            'action1': 'showCurveSet',
            'action2': 'editCurveSet',
            'action2_text': ' (edit) ',
            'whenEmpty' : "You have no curve sets. <a href=" +
                                reverse('createCurveSet', args=[user_id]) + ">Prepare one</a>."
    }
    return HttpResponse(template.render(context, request))

def deleteFile(request, user_id, file_id):
    try:
        user = User.objects.get(id=user_id)
    except:
        user=None

    try:
        file = CurveFile.objects.get(id=file_id)
    except:
        if ( __debug__ ):
            print("File not found with id: %s" % file_id)
        return HttpResponseRedirect(reverse('browseFiles',
            args=[user_id]))

    if request.method == 'POST':
        form = DeleteFileForm(file_id, request.POST)
        if form.is_valid():
            if ( form.process(user, file_id) == True ):
                return HttpResponseRedirect(reverse('browseFiles',
                    args=[user_id]))
    else:
        form = DeleteFileForm(file_id)

    context = { 
            'form': form,
            'file': file,
            'user': user
            }
    return render(request, 'manager/deleteFile.html', context)


def deleteCurve(request, user_id, curve_id):
    try:
        user = User.objects.get(id=user_id)
    except:
        user=None

    try:
        file = Curve.objects.get(id=curve_id)
    except:
        if ( __debug__ ):
            print("Curve not found with id: %s" % file_id)
        return HttpResponseRedirect(reverse('browseFiles',
            args=[user_id]))

    if request.method == 'POST':
        form = DeleteCurveForm(curve_id, request.POST)
        if form.is_valid():
            if ( form.process(user, curve_id) == True ):
                return HttpResponseRedirect(reverse('browseFiles',
                    args=[user_id]))
    else:
        form = DeleteFileForm(curve_id)

    context = { 
            'form': form,
            'curve': curve,
            'user': user
            }
    return render(request, 'manager/deleteCurve.html', context)


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


    template = loader.get_template('manager/showAnalysis.html')
    context = {
            'user' : user,
            'analysis_id': an.id,
            'plot_width' : PlotMaker.plot_width,
            'plot_height' : PlotMaker.plot_height,
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
                return HttpResponseRedirect(reverse('editFile', args=[user_id, file_id]))
    else:
        form = UploadFileForm()

    context = {
            'form': form, 
            'user': user
            }
    return render(request, 'manager/uploadFile.html', context)


def editFile(request, user_id, file_id,):
    try:
        user = User.objects.get(id=user_id)
    except:
        user=None

    if request.method == 'POST':
        form = AddAnalytesForm(user, "File", file_id, request.POST)
        if form.is_valid():
            if ( form.process(user) == True ):
                return HttpResponseRedirect(reverse('browseFiles', args=[user_id]))
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


def showFile(request, user_id, file_id):
    try:
        user = User.objects.get(id=user_id)
    except:
        user=None

    if request.method == 'POST':
        form = SelectXForm(user_id, request.POST)
        if form.is_valid():
            if ( form.process(user) == True ):
                return HttpResponseRedirect(reverse('showFile', args=[user_id, file_id]))
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


def processFile(request, user_id, file_id):
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


def processing(request, user_id, processing_id):
    try:
        user = User.objects.get(id=user_id)
    except:
        user=None
    return True


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
