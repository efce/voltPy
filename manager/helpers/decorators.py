from django.http import HttpResponseRedirect
from django.urls import reverse
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from manager.exceptions import VoltPyNotAllowed, VoltPyDoesNotExists
import manager.helpers as mh


def redirect_on_voltpyexceptions(fun):
    """
    Should handle VoltPy exceptions thrown by functions.
    """
    def wrap(*args, **kwargs):
        request = kwargs.get('request', None)
        if request is None:
            for a in args:
                if hasattr(a, 'session'):
                    request = a
                    break
        try:
            return fun(*args, **kwargs)
        except VoltPyNotAllowed as e:
            print("Got not allowed! ", repr(e))
            mh.functions.add_notification(request, 'Operation not allowed.')
            return HttpResponseRedirect(reverse('index'))
        except VoltPyDoesNotExists as e:
            print("Got does not exists! ", repr(e))
            mh.functions.add_notification(request, 'Object does not exists.')
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
