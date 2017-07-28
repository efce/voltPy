from django.shortcuts import render
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.template import loader
from django.core.urlresolvers import reverse
from django.views.decorators.cache import never_cache
from .models import *
from .forms import *
from .plotmaker import PlotMaker


def indexNoUser(request):
    template = loader.get_template('manager/index.html')
    return HttpResponse(template.render({}, request))


def login(request):
    return HttpResponseRedirect(reverse('index', args=[ 0 ]))


def index(request, user_id):
    template = loader.get_template('manager/index.html')
    return HttpResponse(template.render({ 'user_id': user_id }, request))


def browseFiles(request, user_id):
    try:
        files = CurveFile.objects.filter(owner=user_id, deleted=False)
    except:
        files = None

    if ( __debug__ ):
        print(files)
    template = loader.get_template('manager/browse.html')
    context = {
            'browse_by' : 'files',
            'user_id' : user_id,
            'disp' : files,
            'action1': "setConcentrations",
            'action2': "deleteFile",
            'action2_text': '(delete)',
            'whenEmpty' : "You have no files uploaded. <a href=" + 
                                reverse('upload', args=[user_id]) + ">Upload one</a>."
    }
    return HttpResponse(template.render(context, request))


def browseCalibrations(request, user_id):
    try:
        calibs = CurveCalibrations.objects.filter(owner=user_id)
    except:
        calibs = None

    if ( __debug__ ):
        print(calibs)
    template = loader.get_template('manager/browse.html')
    context = {
            'browse_by' : 'calibrations',
            'user_id' : user_id,
            'disp' : calibs,
            'action1': "showCalibration",
            'action2': '',
            'action2_text': '',
            'whenEmpty' : "You have no calibrations. <a href=" +
                                reverse('prepareCalibration', args=[user_id]) + ">Prepare one</a>."
    }
    return HttpResponse(template.render(context, request))

def deleteFile(request, user_id, file_id):
    try:
        file = CurveFile.objects.get(pk=file_id)
    except:
        if ( __debug__ ):
            print("File not found with id: %s" % file_id)
        return HttpResponseRedirect(reverse('browseFiles',
            args=[user_id]))

    if request.method == 'POST':
        form = DeleteFileForm(file_id, request.POST)
        if form.is_valid():
            if ( form.process(user_id) == True ):
                return HttpResponseRedirect(reverse('browseFiles',
                    args=[user_id]))
    else:
        form = DeleteFileForm(file_id)
    return render(request, 'manager/delete.html', 
            {'form': form,
            'file': file,
            'user_id': user_id})

def prepareCalibration(request, user_id):
    if request.method == 'POST':
        form = SelectCurvesForCalibrationForm(user_id, request.POST)
        if form.is_valid():
            if ( form.process(user_id, request) == True ):
                return HttpResponseRedirect(reverse('browseCalibrations', args=[user_id]))
    else:
        form = SelectCurvesForCalibrationForm(user_id)
    return render(request, 'manager/prepareCalibration.html', {'form': form,
                                                        'user_id': user_id})

def showCalibration(request,user_id, calibration_id):
    try:
        cf = CurveCalibrations.objects.get(pk=calibration_id)
    except:
        cf = None

    if ( __debug__): 
        print(cf)
    template = loader.get_template('manager/showCalibration.html')
    context = {
            'user_id' : user_id,
            'calibration_id': calibration_id,
            #'form' : form
    }
    return HttpResponse(template.render(context, request))

def upload(request, user_id):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            if ( form.process(user_id, request) == True ):
                file_id = form.file_id
                return HttpResponseRedirect(reverse('setConcentrations', args=[user_id, file_id]))
    else:
        form = UploadFileForm()
    return render(request, 'manager/upload_auto.html', {'form': form,
        'user_id': user_id})


def setConcentrations(request, user_id, file_id,):
    if request.method == 'POST':
        form = AddAnalytesForm(user_id, file_id, request.POST)
        if form.is_valid():
            if ( form.process(user_id) == True ):
                return HttpResponseRedirect(reverse('browseCalibrations', args=[user_id]))
    else:
        form = AddAnalytesForm(user_id, file_id)
    return render(request, 'manager/setConcentrations.html', {'form': form,
        'user_id' : user_id, 'file_id' : file_id})

def showFile(request, user_id, curvefile_id):
    if request.method == 'POST':
        form = SelectXForm(user_id, request.POST)
        if form.is_valid():
            if ( form.process(user_id) == True ):
                return HttpResponseRedirect(reverse('showFile', args=[user_id, curvefile_id]))
    else:
        form = SelectXForm(user_id)

    try:
        cf = CurveFile.objects.get(pk=curvefile_id, deleted=False)
    except:
        cf = None

    if ( __debug__): 
        print(cf)
    template = loader.get_template('manager/showFile.html')
    context = {
            'user_id' : user_id,
            'curvefile_id': curvefile_id,
            'form' : form
    }
    return HttpResponse(template.render(context, request))


@never_cache
def generatePlot(request, user_id, plot_type, value_id):
    """
    Allowed types are:
    f - whole file
    c - calibration
    s - sigle curve
    """
    allowedTypes = {
            'f' : 'File',
            'c' : 'Calibration',
            's' : 'SignleCurve'
            }
    if not ( plot_type in allowedTypes ):
        return
    pm = PlotMaker()
    return HttpResponse(pm.getImage(request, user_id, allowedTypes[plot_type],value_id), content_type="image/png")
