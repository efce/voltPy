from django.http import HttpResponseRedirect
from django.urls import reverse
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from manager.exceptions import VoltPyNotAllowed, VoltPyDoesNotExists


def redirect_on_voltpyexceptions(fun):
    """
    Should handle VoltPy exceptions thrown by functions.
    """
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
    """
    Makes sure that user is logged and passes User object to function call.
    """
    @login_required
    def wrap(request, *args, **kwargs):
        try:
            user = request.user
        except (AttributeError, TypeError, ValueError, ObjectDoesNotExist):
            raise VoltPyNotAllowed("Z with usera")
        kwargs['user'] = user
        return fun(request, *args, **kwargs)
    return wrap
