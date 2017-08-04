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


def browseCalibrations(request, user_id):
    try:
        user = User.objects.get(id=user_id)
    except:
        user=None

    try:
        calibs = Calibration.objects.filter(owner=user_id)
    except:
        calibs = None

    if ( __debug__ ):
        print(calibs)
    template = loader.get_template('manager/browse.html')
    context = {
            'browse_by' : 'calibrations',
            'user' : user,
            'disp' : calibs,
            'action1': 'showCalibration',
            'action2': 'editCalibration',
            'action2_text': ' (edit) ',
            'whenEmpty' : "You have no calibrations. <a href=" +
                                reverse('selectCurvesForCalibration', args=[user_id]) + ">Prepare one</a>."
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


def selectCurvesForCalibration(request, user_id):
    try:
        user = User.objects.get(id=user_id)
    except:
        user=None

    if request.method == 'POST':
        form = SelectCurvesForCalibrationForm(user, request.POST)
        if form.is_valid():
            if ( form.process(user) == True ):
                calid = form.calid
                if calid and calid > -1:
                    return HttpResponseRedirect(reverse('editCalibration', args=[user_id, calid]))
    else:
        form = SelectCurvesForCalibrationForm(user)

    context = {
            'form': form, 
            'user': user
            }
    return render(request, 'manager/selectCurvesForCalibration.html', context)

def showCalibration(request, user_id, calibration_id):
    try:
        user = User.objects.get(id=user_id)
    except:
        user=None

    try:
        cf = Calibration.objects.get(id=calibration_id)
    except:
        cf = None

    template = loader.get_template('manager/showCalibration.html')
    context = {
            'user' : user,
            'calibration_id': calibration_id,
            'plot_width' : PlotMaker.plot_width,
            'plot_height' : PlotMaker.plot_height,
    }
    return HttpResponse(template.render(context, request))

def editCalibration(request,user_id,calibration_id):
    try:
        user = User.objects.get(id=user_id)
    except:
        user=None

    if request.method == 'POST':
        if ( 'submitGenerate' in request.POST ):
            formGenerate = generateCalibrationForm(request.POST)
            if ( formGenerate.is_valid() ):
                formGenerate.process(user, calibration_id)
                return HttpResponseRedirect(reverse('showCalibration', args=[user_id, calibration_id]))
        else:
            formGenerate = generateCalibrationForm()

        if ( 'submitFormAnalyte' in request.POST ):
            formAnalyte = AddAnalytesForm(user, "Calibration", calibration_id, request.POST)
            if formAnalyte.is_valid():
                if ( formAnalyte.process(user) == True ):
                    return HttpResponseRedirect(reverse('showCalibration', args=[user_id, calibration_id]))
        else:
            formAnalyte = AddAnalytesForm(user, "Calibration", calibration_id)

        if ( 'submitFormRange' in request.POST ):
            formRange = SelectRange(calibration_id, request.POST)
            if formRange.is_valid():
                if ( formRange.process(user, calibration_id) == True ):
                    return HttpResponseRedirect(reverse('showCalibration', args=[user_id, calibration_id]))
        else:
            formRange = SelectRange(calibration_id)

    else:
        formAnalyte = AddAnalytesForm(user, "Calibration", calibration_id)
        formRange = SelectRange(calibration_id)
        formGenerate = generateCalibrationForm()

    try:
        cal = Calibration.objects.get(id=calibration_id)
        if not cal.canBeReadBy(user):
            raise 3
    except:
        raise 404

    cal_disp = ""
    for c in cal.usedCurveData.all():
        cal_disp += ("%i," % c.curve.id)
    cal_disp = cal_disp[:-1]
    context = { 
            'formAnalyte': formAnalyte, 
            'formRange': formRange,
            'formGenerate' : formGenerate,
            'user' : user, 
            'calibration_id' : calibration_id, 
            'plot_width' : PlotMaker.plot_width,
            'plot_height' : PlotMaker.plot_height,
            'cal_disp': cal_disp
            }
    return render(request, 'manager/editCalibration.html', context)


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

    try:
        user = User.objects.get(id=user_id)
    except:
        user=None

    pm = PlotMaker()
    if (plot_type == 'f' ):
        pm.processFile(user, value_id)
    elif (plot_type == 's'):
        pm.processCurves(user, value_id)
    elif (plot_type == 'c'):
        pm.processCalibration(user, value_id)

    return HttpResponse(
            pm.getPage(), 
            content_type="text/html" 
        )
