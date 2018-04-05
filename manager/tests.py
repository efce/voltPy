import io
import os
import json
from pathlib import Path
from django.test import TestCase
from django.utils import timezone
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.test.client import RequestFactory
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
import manager.models as mmodels
import manager.uploads.uploadmanager as um
import manager.operations.methodmanager as mm
from manager.exceptions import VoltPyDoesNotExists,VoltPyFailed,VoltPyFailed

# Create your tests here.
"""
Test should:
    add user
    login as user
    upload file
    create curve set
    process file
    check the result of processing
"""

uname = 'ssssss'  # 'TESTźćµó'
upass = '!@#ASDŁÓĘ®ŊŒŊŚŒĘ'


def addFilesToRequest(request, filepaths_list, post_name='files[]'):
    _filelist = []
    for filepath in filepaths_list:
        test_file = Path(filepath)
        assert test_file.is_file()
        with open(test_file.absolute(), "rb") as ufile:
            bytefile = io.BytesIO(ufile.read())
            fsize = ufile.tell()
            fname = ufile.name
        inmemoryfile = InMemoryUploadedFile(bytefile, 'file', fname, None, fsize, None)
        _filelist.append(inmemoryfile)
    request.FILES.setlist(post_name, _filelist)
    return request


def uploadFiles(user, list_of_files=None):
    if list_of_files is None:
        file_list = ['./test_files/test_file.volt']
    else:
        file_list = list_of_files
    factory = RequestFactory()
    postdata = {}
    for fid, fn in enumerate(file_list):
        testname = "tęśß ńąµę"
        testcomment = "ßęśß ćóµµęńß"
        rstr = 'f_%i_%s'
        postdata[rstr % (fid, 'firstColumn')] = 'firstIsE'
        postdata[rstr % (fid, 'voltMethod')] = 'dpv'
        postdata[rstr % (fid, 'currentUnit')] = 'µA'
        postdata[rstr % (fid, 'ignoreRows')] = '0'
        postdata[rstr % (fid, 'firstColumn_dE')] = '30'
        postdata[rstr % (fid, 'firstColumn_t')] = '10'
    postdata['fileset_name'] = 'test'
    postdata['command'] = 'upload'
    request = factory.post('/', data=postdata)
    request.user = user
    request.session = {}
    request = addFilesToRequest(request, file_list, 'files[]')
    pu = um.ajax(request=request)


class TestUser(TestCase):
    def setUp(self):
        user = User.objects.create_user(
            username=uname,
            email='test@test.test',
            password=upass
        )
        user.save()

    def test_user(self):
        us = User.objects.all()
        self.assertEqual(us[0].username, uname)
        user = authenticate(username=uname, password=upass)
        self.assertIsNotNone(user)


class TestFileUpload(TestCase):
    listOfFields = {
        'ignoreRows': None,  # int 
        'currentUnit': {
            'nA': [],
            'µA': [],
            'mA': [],
            'A': [],
        },
        'firstColumn': {
            'firstIsE': [
                'firstColumn_t',   # float
                'firstColumn_dE',  # float
            ],
            'firstIsT': [
                'firstColumn_Ep',  # float
                'firstColumn_Ek',  # float
                'firstColumn_dE',  # float
            ],
            'firstIsI': [
                'firstColumn_Ep',  # float
                'firstColumn_Ek',  # float
                'firstColumn_dE',  # float
                'firstColumn_t',   # float
            ],
        },
        'isSampling': {
            'on': [
                'isSampling_SPP',    # int Samples Per Point
                'isSampling_SFreq',  # float 
            ],
            None: []
        },
        'voltMethod': {
            'lsv': [],
            'scv': [],
            'npv': [],
            'dpv': [],
            'swv': [],
            'chonoamp': []
        }
    }

    file_list = [
        './test_files/test_file.txt',
        './test_files/test_file.csv',
        './test_files/test_file.xls',
        './test_files/test_file.xlsx',
        './test_files/test_file.ods',
        './test_files/test_file.vol',
    ]

    file_list_fail = [
        './test_files/test_file_fail.csv',
        './test_files/test_file_fail.volt',
        './test_files/test_file_fail.xls',
    ]

    file_list_sampling = [
        './test_files/test_file_sampling.txt',
        './test_files/test_file_sampling.csv',
        './test_files/test_file_sampling.xls',
        './test_files/test_file_sampling.xlsx',
        './test_files/test_file_sampling.ods',
        './test_files/test_file.volt',
        './test_files/test_file.voltc',
    ]
    curves_per_file = 24
    curve_length = 250
    sampling_length = 10000

    def setUp(self):
        u = User.objects.create_user(
            username=uname,
            email='test@test.test',
            password=upass
        )
        u.save()
        self.user = authenticate(username=uname, password=upass)
        self.user2 = User.objects.create_user(
            username='ASDASDDA',
            email='test@test.test',
            password=upass
        )

    def test_file_upload(self):
        factory = RequestFactory()
        postdata = {}
        for fid, filepath in enumerate(self.file_list):
            testname = "tęśß ńąµę"
            testcomment = "ßęśß ćóµµęńß"
            rstr = 'f_%i_%s'
            postdata[rstr % (fid, 'firstColumn')] = 'firstIsE'
            postdata[rstr % (fid, 'voltMethod')] = 'dpv'
            postdata[rstr % (fid, 'currentUnit')] = 'µA'
            postdata[rstr % (fid, 'ignoreRows')] = '0'
            postdata[rstr % (fid, 'firstColumn_dE')] = '30'
            postdata[rstr % (fid, 'firstColumn_t')] = '10'
            #postdata[rstr % (fid, 'isSampling')] = \
                    #        None
            #postdata[rstr % (fid, 'isSampling_SPP')] = \
                    #       1
            #postdata[rstr % (fid, 'isSampling_SFreq')] = \
                    #       1
        postdata['command'] = 'upload'
        postdata['fileset_name'] = '";drop tables; Test SĘ™ÆŚĆ<≤≥≠²³¢'
        request = factory.post('/', data=postdata)
        request.user = self.user
        request.session = {}
        request = addFilesToRequest(request, self.file_list, 'files[]')
        pu = um.ajax(request=request)
        self.assertEqual(200, pu.status_code, 'code 200 expected')
        ret = json.loads(pu.content)
        if 'success' not in ret['command']:
            self.fail('success not reported by uploadmanager')

        fileset = mmodels.FileSet.objects.all()[0]
        self.assertEqual(len(self.file_list), len(fileset.files.all()), 'incomplete fileset')
        for f in fileset.files.all():
            cs = f.curveSet
            self.assertEqual(len(cs.curvesData.all()), self.curves_per_file)
            for cd in cs.curvesData.all():
                self.assertEqual(self.curve_length, len(cd.current), f.fileName)
                float(cd.current[3])  # Test random element - selected by a dice roll
                float(cd.potential[3])
                float(cd.time[3])
                self.assertTrue(cd.canBeReadBy(self.user))
                self.assertTrue(cd.canBeUpdatedBy(self.user))
                self.assertTrue(cd.isOwnedBy(self.user))
                self.assertFalse(cd.canBeReadBy(self.user2))
                self.assertFalse(cd.canBeUpdatedBy(self.user2))
                self.assertFalse(cd.isOwnedBy(self.user2))
        # TODO: more tests

        # Negative tests:
        for fpath in self.file_list_fail:
            self.assertRaises(VoltPyFailed, uploadFiles, user=self.user, list_of_files=[fpath])


class TestMethodManager(TestCase):
    testmethod = """
import manager.operations.method as method

class TestMethod(method.ProcessingMethod):
    _steps = [
    ]

    def __str__(self):
        return "TestMethod"

    def apply(self, curveSet):
        return

    def finalize(self, user):
        self.model.customData['FINALIZED'] = user.id
        self.model.step = None
        self.model.completed = True
        self.model.save()

    def getFinalContent(self, request, user):
        return { 'head': '', 'body': '' }

main_class = TestMethod
    """

    def setUp(self):
        u = User.objects.create_user(
            username=uname,
            email='test@test.test',
            password=upass
        )
        u.save()
        self.user = authenticate(username=uname, password=upass)
        uploadFiles(self.user)
        self.curveset = mmodels.CurveSet.objects.all()[0]
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.methods_path = os.path.join(BASE_DIR, 'manager', 'operations', 'methods')
        self.assertTrue(os.path.isdir(self.methods_path))
        self.testmethodfile = os.path.join(self.methods_path, 'TestMethod.py')
        with open(self.testmethodfile, 'w') as f:
            f.write(self.testmethod)
        self.assertTrue(os.path.isfile(self.testmethodfile))

    def tearDown(self):
        os.remove(self.testmethodfile)

    def test_methods_load(self):
        mema = mm.MethodManager(user=self.user, curveset_id=self.curveset.id)
        self.assertTrue(mema.methods.get('processing', False))
        self.assertTrue(mema.methods.get('analysis', False))
        self.assertEqual(mema.methods['processing']['TestMethod'].__name__, 'TestMethod')

    def test_methods_usage(self):
        p = mmodels.Processing(
            owner=self.user,
            curveSet=self.curveset,
            date=timezone.now(),
            name='PROC',
            method='TestMethod',
            active_step_num=0,
            deleted=False,
            completed=False
        )
        p.save()
        mema = mm.MethodManager(user=self.user, processing_id=p.id)

        class req:
            method = 'POST'
            POST = {}

            def __init__(self):
                self.POST['query'] = 'methodmanager'

        request = req()
        mema.process(request=request, user=self.user)
        p = mmodels.Processing.objects.get(id=p.id)
        self.assertEqual(p.customData['FINALIZED'], self.user.id)
