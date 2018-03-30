from django.http import HttpResponseRedirect
from django.urls import reverse
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from manager.exceptions import VoltPyNotAllowed, VoltPyDoesNotExists
import manager.models as mmodels

def redirect_on_voltpyexceptions(fun):
    def wrap(*args, **kwargs):
        try:
            return fun(*args, **kwargs)
        except VoltPyNotAllowed as e:
            print("Got not allowed! ", repr(e))
            return HttpResponseRedirect(reverse('index'))
        except VoltPyDoesNotExists as e:
            print("Got does not exists! ", repr(e))
            return HttpResponseRedirect(reverse('index'))
    return wrap


def with_user(fun):
    @login_required
    def wrap(request, *args, **kwargs):
        try:
            user = request.user
        except (AttributeError, TypeError, ValueError, ObjectDoesNotExist):
            raise VoltPyNotAllowed("Z with usera")
        kwargs['user'] = user
        return fun(request,*args, **kwargs)
    return wrap

