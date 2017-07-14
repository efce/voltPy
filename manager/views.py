from django.shortcuts import render
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.template import loader
from django.core.urlresolvers import reverse
from .models import *
from .forms import UploadFileForm


def index(request):
    template = loader.get_template('manager/index.html')
    return HttpResponse(template.render({}, request))


def browse(request, user_id):
    try:
        files = CurveFile.objects.filter(owner=user_id)
    except:
        files = None

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


def show(request, user_id, curvevectors_id):
    return HttpResponse("Showing plot %s of user %s" % (curvevectors_id, user_id))


def upload(request, user_id):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            form.process(user_id, request)
            return HttpResponseRedirect(reverse('browse', args=[user_id]))
    else:
        form = UploadFileForm()
    return render(request, 'manager/upload_auto.html', {'form': form})

