from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^(?P<user_id>[0-9]+)/browse/$', views.browse, name='browse'),
    url(r'^(?P<user_id>[0-9]+)/show/(?P<curvevectors_id>[0-9]+)$', views.show, name='show'),
    url(r'^(?P<user_id>[0-9]+)/upload/$', views.upload, name='upload'),
    url(r'^(?P<user_id>[0-9]+)/plot/(?P<curvevectors_id>[0-9]+)$', views.plot, name='plot'),
]
