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
        calibs = Calibration.objects.filter(owner=user_id)
    except:
        calibs = None

    if ( __debug__ ):
        print(calibs)
    template = loader.get_template('manager/browse.html')
    context = {
            'browse_by' : 'calibrations',
            'user_id' : user_id,
            'disp' : calibs,
            'action1': 'showCalibration',
            'action2': 'editCalibration',
            'action2_text': ' (edit) ',
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
            if ( form.process(user_id) == True ):
                calid = form.calid
                if calid and calid > -1:
                    return HttpResponseRedirect(reverse('editCalibration', args=[user_id, calid]))
    else:
        form = SelectCurvesForCalibrationForm(user_id)
    return render(request, 'manager/prepareCalibration.html', {'form': form,
                                                        'user_id': user_id})

def showCalibration(request, user_id, calibration_id):
    try:
        cf = Calibration.objects.get(pk=calibration_id)
    except:
        cf = None

    if ( __debug__): 
        print(cf)
    template = loader.get_template('manager/showCalibration.html')
    context = {
            'user_id' : user_id,
            'calibration_id': calibration_id,
            'plot_width' : PlotMaker.plot_width,
            'plot_height' : PlotMaker.plot_height,
            #'form' : form
    }
    return HttpResponse(template.render(context, request))

def editCalibration(request,user_id,calibration_id):
    if request.method == 'POST':
        if ( 'submitGenerate' in request.POST ):
            formGenerate = generateCalibrationForm(request.POST)
            print('gen submitted')
            if ( formGenerate.is_valid() ):
                print('gen is valid')
                formGenerate.process(user_id, calibration_id)
                print('gen processed')
                return HttpResponseRedirect(reverse('showCalibration', args=[user_id, calibration_id]))
        else:
            formGenerate = generateCalibrationForm()


        if ( 'submitFormAnalyte' in request.POST ):
            formAnalyte = AddAnalytesForm(user_id, "Calibration", calibration_id, request.POST)
            if formAnalyte.is_valid():
                if ( formAnalyte.process(user_id) == True ):
                    return HttpResponseRedirect(reverse('showCalibration', args=[user_id, calibration_id]))
        else:
            formAnalyte = AddAnalytesForm(user_id, "Calibration", calibration_id)

        if ( 'submitFormRange' in request.POST ):
            formRange = SelectRange(calibration_id, request.POST)
            if formRange.is_valid():
                if ( formRange.process(user_id, calibration_id) == True ):
                    return HttpResponseRedirect(reverse('showCalibration', args=[user_id, calibration_id]))
        else:
            formRange = SelectRange(calibration_id)

    else:
        formAnalyte = AddAnalytesForm(user_id, "Calibration", calibration_id)
        formRange = SelectRange(calibration_id)
        formGenerate = generateCalibrationForm()

    cal = Calibration(pk=calibration_id)
    cal_disp = ""
    for c in cal.usedCurveData.all():
        cal_disp += ("%i," % c.curve.id)
    cal_disp = cal_disp[:-1]
    context = { 
            'formAnalyte': formAnalyte, 
            'formRange': formRange,
            'formGenerate' : formGenerate,
            'user_id' : user_id, 
            'calibration_id' : calibration_id, 
            'plot_width' : PlotMaker.plot_width,
            'plot_height' : PlotMaker.plot_height,
            'cal_disp': cal_disp
            }
    return render(request, 'manager/editCalibration.html', context)

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
        form = AddAnalytesForm(user_id, "File", file_id, request.POST)
        if form.is_valid():
            if ( form.process(user_id) == True ):
                return HttpResponseRedirect(reverse('browseCalibrations', args=[user_id]))
    else:
        form = AddAnalytesForm(user_id, "File", file_id)
    context = {
            'user_id' : user_id, 
            'file_id' : file_id,
            'form': form,
            'plot_width' : PlotMaker.plot_width,
            'plot_height' : PlotMaker.plot_height
            }
    return render(request, 'manager/setConcentrations.html', context)

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
            'plot_width' : PlotMaker.plot_width,
            'plot_height' : PlotMaker.plot_height,
            'form' : form
    }
    return HttpResponse(template.render(context, request))


@never_cache
def generatePlot(request, user_id, plot_type, value_id):
    """
    Allowed types are:
    f - whole file
    c - calibration
    s - setup curves
    """
    allowedTypes = {
            'f' : 'File',
            'c' : 'Calibration',
            's' : 'Curves'
            }
    if not ( plot_type in allowedTypes ):
        return
    pm = PlotMaker()
    return HttpResponse(
            pm.getPage(
                request, 
                user_id, 
                allowedTypes[plot_type],
                value_id), 
            content_type="text/html" )
