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
        views.browseFilesets, name='browseFilesets'),
    url(r'^browse-filesets/(?P<page_number>[0-9]+)/$', 
        views.browseFilesets, name='browseFilesets'),
    url(r'^browse-files/$',
        views.browseFiles, name='browseFiles'),
    url(r'^browse-files/(?P<page_number>[0-9]+)/$', 
        views.browseFiles, name='browseFiles'),
    url(r'^upload-fileset/$',
        views.upload, name='upload'),
    url(r'^ajax/uploads/$',
        uploadmanager.ajax, name='ajaxUpload'),
    url(r'^ajax/search-dataset/$',
        views.searchDataset, name='searchDatasetAjax'),
    url(r'^ajax/get-shareable/$',
        views.getShareable, name='getShareable'),
    url(r'^ajax/plot-interaction/$',
        views.plotInteraction, name='plotInteraction'),
    url(r'^delete-fileset/(?P<fileset_id>[0-9]+)/$',
        views.deleteFileset, name='deleteFileset'),
    url(r'^delete-file/(?P<file_id>[0-9]+)/$',
        views.deleteFile, name='deleteFile'),
    url(r'^show-file/(?P<file_id>[0-9]+)/$',
        views.showFile, name='showFile'),
    url(r'^show-fileset/(?P<fileset_id>[0-9]+)/$',
        views.showFileset, name='showFileset'),
    url(r'^delete-curve/(?P<obj_type>[file|dataset]+)/(?P<obj_id>[0-9]+)/(?P<to_delete_id>[0-9]+)/$',
        views.deleteCurve, name='deleteCurve'),
    url(r'^export/(?P<obj_type>[fileset|file|dataset|analysis]+)/(?P<obj_id>[0-9]+)/$',
        views.export, name='export'),
    url(r'^browse-datasets/$',
        views.browseDatasets, name='browseDatasets'),
    url(r'^browse-datasets/(?P<page_number>[0-9]+)/$', 
        views.browseDatasets, name='browseDatasets'),
    url(r'^create-dataset/$',
        views.createDataset, name='createDataset'),
    url(r'^clone-dataset/(?P<to_clone_id>[0-9]+)/$',
        views.cloneDataset, name='cloneDataset'),
    url(r'^delete-from-dataset/(?P<dataset_id>[0-9]+)/$',
        views.deleteFromDataset, name='deleteFromDataset'),
    url(r'^delete-from-file/(?P<file_id>[0-9]+)/$',
        views.deleteFromFile, name='deleteFromFile'),
    url(r'^clone-file/(?P<to_clone_id>[0-9]+)/$',
        views.cloneFile, name='cloneFile'),
    url(r'^clone-fileset/(?P<to_clone_id>[0-9]+)/$',
        views.cloneFileset, name='cloneFileset'),
    url(r'^show-dataset/(?P<dataset_id>[0-9]+)/$',
        views.showDataset, name='showDataset'),
    url(r'^undo-dataset/(?P<dataset_id>[0-9]+)/$',
        views.undoDataset, name='undoDataset'),
    url(r'^edit-analyte/(?P<obj_type>[file|dataset]+)/(?P<obj_id>[0-9]+)/(?P<analyte_id>[0-9|new]+)/$',
        views.editAnalyte, name='editAnalyte'),
    url(r'^edit-curves/(?P<obj_type>[file|dataset]+)/(?P<obj_id>[0-9]+)/$',
        views.editCurves, name='editCurves'),
    url(r'^apply-model/(?P<obj_type>[an|pr]+)/(?P<obj_id>[0-9]+)/(?P<dataset_id>[0-9|new]+)/$',
        views.applyModel, name='applyModel'),
    url(r'^delete-dataset/(?P<dataset_id>[0-9]+)/$',
        views.deleteDataset, name='deleteDataset'),
    url(r'^analyze/(?P<analysis_id>[0-9]+)/$',
        views.analyze, name='analyze'),
    url(r'^process/(?P<processing_id>[0-9]+)/$',
        views.process, name='process'),
    url(r'^show-analysis/(?P<analysis_id>[0-9]+)/$',
        views.showAnalysis, name='showAnalysis'),
    url(r'^browse-analysis/$',
        views.browseAnalysis, name='browseAnalysis'),
    url(r'^browse-analysis/(?P<page_number>[0-9]+)/$', 
        views.browseAnalysis, name='browseAnalysis'),
    url(r'^delete-analysis/(?P<analysis_id>[0-9]+)/$',
        views.deleteAnalysis, name='deleteAnalysis'),
    url(r'^share/(?P<link_hash>[0-9a-zA-Z]+)/$',
        views.shareLink, name='shareLink'),
    url(r'^unshare/(?P<share_id>[0-9]+)/$',
        views.unshare, name='unshare'),
    url(r'^settings/$',
        views.settings, name='settings'),
    url(r'^sharing/$',
        views.sharing, name='sharing'),
    url(r'^show-processed/(?P<processing_id>[0-9]+)/$',
        views.showProcessed, name='showProcessed'),
    url(r'^account_activation_sent/$',
        views.account_activation_sent, name='account_activation_sent'),
    url(r'^change-password/$',
        views.changePassword, name='changePassword'),
    url(r'^change-email/$',
        views.changeEmail, name='changeEmail'),
    url(r'^activate/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        views.activate, name='activate'),
    url(r'^confirm-new-email/(?P<uid>[0-9]+)/(?P<token>[0-9A-Za-z]+)/$',
        views.confirmNewEmail, name='confirmNewEmail'),
    url(r'^accept-cookies/',
        views.acceptCookies, name='acceptCookies'),
    url(r'^terms-of-service/',
        views.termsOfService, name='termsOfService'),
    url(r'^privacy-policy/',
        views.privacyPolicy, name='privacyPolicy'),
]

urlpatterns += [
            path('', include('django.contrib.auth.urls')),
]
