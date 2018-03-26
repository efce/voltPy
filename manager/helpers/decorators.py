from django.http import HttpResponseRedirect
from django.urls import reverse
from django.core.exceptions import ObjectDoesNotExist
from manager.exceptions import VoltPyNotAllowed, VoltPyDoesNotExists
import manager.models as mmodels

def redirect_on_voltpyexceptions(fun):
    def wrap(*args, **kwargs):
        user = kwargs.get('user', None)
        try:
            return fun(*args, **kwargs)
        except VoltPyNotAllowed as e:
            print("Got not allowed! ", repr(e))
            if user is None:
                return HttpResponseRedirect(reverse('indexNoUser'))
            else:
                return HttpResponseRedirect(reverse('index'))
        except VoltPyDoesNotExists as e:
            print("Got does not exists! ", repr(e))
            if user is None:
                return HttpResponseRedirect(reverse('indexNoUser'))
            else:
                return HttpResponseRedirect(reverse('index'))
    return wrap

def with_user(fun):
    def wrap(*args, **kwargs):
        user_id = kwargs.pop('user_id', None)
        try:
            user_id = int(user_id)
            user = mmodels.User.objects.get(id=user_id)
        except (TypeError, ValueError, ObjectDoesNotExist):
            raise VoltPyNotAllowed(None)
        kwargs['user'] = user
        return fun(*args, **kwargs)
    return wrap

