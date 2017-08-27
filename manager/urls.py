from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', 
        views.indexNoUser, name='indexNoUser'),
    url(r'^(?P<user_id>[0-9]+)/$', 
        views.index, name='index'),
    url(r'^login/$', 
        views.login, name='login'),
    url(r'^logout/$', 
        views.logout, name='logout'),
    url(r'^(?P<user_id>[0-9]+)/browse-files/$', 
        views.browseFiles, name='browseFiles'),
    url(r'^(?P<user_id>[0-9]+)/upload-file/$', 
        views.upload, name='upload'),
    url(r'^(?P<user_id>[0-9]+)/delete-file/(?P<file_id>[0-9]+)/$', 
        views.deleteFile, name='deleteFile'),
    url(r'^(?P<user_id>[0-9]+)/edit-file/(?P<file_id>[0-9]+)/$', 
        views.editFile, name='editFile'),
    url(r'^(?P<user_id>[0-9]+)/show-file/(?P<file_id>[0-9]+)/$', 
        views.showFile, name='showFile'),
    url(r'^(?P<user_id>[0-9]+)/delete-curve/(?P<curve_id>[0-9]+)/$', 
        views.deleteCurve, name='deleteCurve'),
    url(r'^(?P<user_id>[0-9]+)/generate-plot/(?P<plot_type>[a-z]+)/(?P<value_id>[0-9,]+)/$',
        views.generatePlot, name='generatePlot'),
    url(r'^(?P<user_id>[0-9]+)/browse-curvesets/$', 
        views.browseCurveSets, name='browseCurveSets'),
    url(r'^(?P<user_id>[0-9]+)/create-curve-set/$', 
        views.createCurveSet, name='createCurveSet'),
    url(r'^(?P<user_id>[0-9]+)/show-curveset/(?P<curveset_id>[0-9]+)/$', 
        views.showCurveSet, name='showCurveSet'),
    url(r'^(?P<user_id>[0-9]+)/edit-curveset/(?P<curveset_id>[0-9]+)/$', 
        views.editCurveSet, name='editCurveSet'),
    url(r'^(?P<user_id>[0-9]+)/analyze/(?P<analysis_id>[0-9]+)/$', 
        views.analyze, name='analyze'),
    url(r'^(?P<user_id>[0-9]+)/show-analysis/(?P<analysis_id>[0-9]+)/$', 
        views.showAnalysis, name='showAnalysis'),
    url(r'^(?P<user_id>[0-9]+)/browse-analysis/$', 
        views.browseAnalysis, name='browseAnalysis'),
    url(r'^(?P<user_id>[0-9]+)/delete-analysis/(?P<analysis_id>[0-9]+)/$', 
        views.deleteAnalysis, name='deleteAnalysis'),
    url(r'^(?P<user_id>[0-9]+)/edit-analysis/(?P<analysis_id>[0-9]+)/$', 
        views.editAnalysis, name='editAnalysis'),
    url(r'^(?P<user_id>[0-9]+)/process-curveset/(?P<curveset_id>[0-9]+)/$', 
        views.processCurveSet, name='processCurveSet'),
    url(r'^(?P<user_id>[0-9]+)/process-file/(?P<file_id>[0-9]+)/$', 
        views.processFile, name='processFile'),
    url(r'^(?P<user_id>[0-9]+)/show-processed/(?P<processing_id>[0-9]+)/$', 
        views.showProcessed, name='showProcessed'),
]
