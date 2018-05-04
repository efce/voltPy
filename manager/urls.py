from django.conf.urls import url
from django.urls import include, path
from manager.uploads import uploadmanager
from manager import views

urlpatterns = [
    url(r'^$',
        views.index, name='index'),
    url(r'^register/$',
        views.register, name='register'),
    url(r'^browse-filesets/$',
        views.browseFileSet, name='browseFileSets'),
    url(r'^browse-files/$',
        views.browseCurveFile, name='browseCurveFiles'),
    url(r'^upload-file/$',
        views.upload, name='upload'),
    url(r'^ajax/uploads/$',
        uploadmanager.ajax, name='ajaxUpload'),
    url(r'^ajax/search-curveset/$',
        views.searchCurveSet, name='searchCurveSetAjax'),
    url(r'^ajax/get-shareable/$',
        views.getShareable, name='getShareable'),
    url(r'^ajax/plot-interaction/$',
        views.plotInteraction, name='plotInteraction'),
    url(r'^delete-fileset/(?P<fileset_id>[0-9]+)/$',
        views.deleteFileSet, name='deleteFileSet'),
    url(r'^delete-file/(?P<file_id>[0-9]+)/$',
        views.deleteCurveFile, name='deleteCurveFile'),
    url(r'^show-file/(?P<file_id>[0-9]+)/$',
        views.showCurveFile, name='showCurveFile'),
    url(r'^show-fileset/(?P<fileset_id>[0-9]+)/$',
        views.showFileSet, name='showFileSet'),
    url(r'^delete-curve/(?P<objType>[cf|cs]+)/(?P<objId>[0-9]+)/(?P<delId>[0-9]+)/$',
        views.deleteCurve, name='deleteCurve'),
    url(r'^export/(?P<objType>[fs|cs|cf|an]+)/(?P<objId>[0-9]+)/$',
        views.export, name='export'),
    url(r'^browse-curvesets/$', 
        views.browseCurveSet, name='browseCurveSets'),
    url(r'^create-curveset/$', 
        views.createCurveSet, name='createCurveSet'),
    url(r'^clone-curveset/(?P<toCloneId>[0-9]+)/$',
        views.cloneCurveSet, name='cloneCurveSet'),
    url(r'^clone-curvefile/(?P<toCloneId>[0-9]+)/$',
        views.cloneCurveFile, name='cloneCurveFile'),
    url(r'^clone-fileset/(?P<toCloneId>[0-9]+)/$',
        views.cloneFileSet, name='cloneFileSet'),
    url(r'^show-curveset/(?P<curveset_id>[0-9]+)/$',
        views.showCurveSet, name='showCurveSet'),
    url(r'^undo-curveset/(?P<curveset_id>[0-9]+)/$',
        views.undoCurveSet, name='undoCurveSet'),
    url(r'^edit-analyte/(?P<objType>[cf|cs]+)/(?P<objId>[0-9]+)/(?P<analyteId>[0-9|new]+)/$',
        views.editAnalyte, name='editAnalyte'),
    url(r'^apply-model/(?P<objType>[an|pr]+)/(?P<objId>[0-9]+)/(?P<curveset_id>[0-9|new]+)/$',
        views.applyModel, name='applyModel'),
    url(r'^delete-curveset/(?P<curveset_id>[0-9]+)/$',
        views.deleteCurveSet, name='deleteCurveSet'),
    url(r'^analyze/(?P<analysis_id>[0-9]+)/$',
        views.analyze, name='analyze'),
    url(r'^process/(?P<processing_id>[0-9]+)/$',
        views.process, name='process'),
    url(r'^show-analysis/(?P<analysis_id>[0-9]+)/$',
        views.showAnalysis, name='showAnalysis'),
    url(r'^browse-analysis/$',
        views.browseAnalysis, name='browseAnalysis'),
    url(r'^delete-analysis/(?P<analysis_id>[0-9]+)/$',
        views.deleteAnalysis, name='deleteAnalysis'),
    url(r'^share/(?P<link_hash>[0-9a-zA-Z]+)/$',
        views.shareLink, name='shareLink'),
    url(r'^show-processed/(?P<processing_id>[0-9]+)/$',
        views.showProcessed, name='showProcessed'),
    url(r'^account_activation_sent/$',
        views.account_activation_sent, name='account_activation_sent'),
    url(r'^activate/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        views.activate, name='activate'),
]

urlpatterns += [
            path('', include('django.contrib.auth.urls')),
]
