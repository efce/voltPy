from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^(?P<user_id>[0-9]+)/browse/$', views.browse, name='browse'),
    url(r'^(?P<user_id>[0-9]+)/upload/$', views.upload, name='upload'),
    url(r'^(?P<user_id>[0-9]+)/show/(?P<curvefile_id>[0-9]+)$', views.showFile, name='showFile'),
    url(r'^(?P<user_id>[0-9]+)/plot/(?P<curvefile_id>[0-9]+)/', views.plotFile, name='plotFile'),
]
