from django.shortcuts import render
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.template import loader
from django.core.urlresolvers import reverse
from django.views.decorators.cache import never_cache
from .models import *
from .forms import UploadFileForm, SelectXForm
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
        files = CurveFile.objects.filter(owner=user_id)
    except:
        files = None

    if ( __debug__ ):
        print(files)
    template = loader.get_template('manager/browse.html')
    context = {
            'browse_by' : 'files',
            'user_id' : user_id,
            'disp' : files,
            'action': "showFile",
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
            'action': "showCalibration",
            'whenEmpty' : "You have no calibrations. <a href=" +
                                reverse('prepareCalibration', args=[user_id]) + ">Prepare one</a>."
    }
    return HttpResponse(template.render(context, request))
    pass

def prepareCalibration(request, user_id):
    pass

def showCalibration(request,user_id, calibration_id):
    pass

def upload(request, user_id):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            if ( form.process(user_id, request) == True ):
                return HttpResponseRedirect(reverse('browseFiles', args=[user_id]))
    else:
        form = UploadFileForm()
    return render(request, 'manager/upload_auto.html', {'form': form,
        'user_id': user_id})


def showFile(request, user_id, curvefile_id):
    if request.method == 'POST':
        form = SelectXForm(user_id, request.POST, request.FILES)
        if form.is_valid():
            if ( form.process(user_id, request) == True ):
                return HttpResponseRedirect(reverse('showFile', args=[user_id, curvefile_id]))
    else:
        form = SelectXForm(user_id)

    try:
        cf = CurveFile.objects.get(pk=curvefile_id)
    except:
        cf = None

    if ( __debug__): 
        print(cf)
    template = loader.get_template('manager/show.html')
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
