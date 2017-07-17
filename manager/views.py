from django.shortcuts import render
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.template import loader
from django.core.urlresolvers import reverse
from django.views.decorators.cache import never_cache
from .models import *
from .forms import UploadFileForm
from .voltplot import VoltPlot


def index(request):
    template = loader.get_template('manager/index.html')
    return HttpResponse(template.render({}, request))


def browse(request, user_id):
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
            'files' : files,
            'url_upload' : reverse('upload', args=[ user_id ]),
    }
    return HttpResponse(template.render(context, request))


def broseByFile(request, user_id):
    pass


def browseByCalibration(request, user_id):
    pass


def upload(request, user_id):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            if ( form.process(user_id, request) == True ):
                return HttpResponseRedirect(reverse('browse', args=[user_id]))
    else:
        form = UploadFileForm()
    return render(request, 'manager/upload_auto.html', {'form': form})


def showFile(request, user_id, curvefile_id):
    try:
        cf = CurveFile.objects.get(pk=curvefile_id)
    except:
        cf = None

    if ( __debug__): 
        print(cf)
    template = loader.get_template('manager/show.html')
    context = {
            'user_id' : user_id,
            'curvefile_id': curvefile_id
    }
    return HttpResponse(template.render(context, request))


@never_cache
def plotFile(request, user_id, curvefile_id):
    vp = VoltPlot()
    return HttpResponse(vp.getImageFromFile(user_id, curvefile_id), content_type="image/png")

    #    try:
    #        with open(valid_image, "rb") as f:
    #            return HttpResponse(f.read(), content_type="image/jpeg")
    #    except IOError:
    #        red = Image.new('RGBA', (1, 1), (255,0,0,0))
    #        response = HttpResponse(content_type="image/jpeg")
    #        red.save(response, "JPEG")
    #        return response
