import io
import os
import json
from pathlib import Path
from django.test import TestCase
from django.utils import timezone
from django.utils.datastructures import MultiValueDict
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.test.client import RequestFactory
import manager.models as mmodels
import manager.uploads.uploadmanager as um
import manager.operations.methodmanager as mm

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


def uploadFile(user):
    file_list = ['./test_files/test_file.volt']
    factory = RequestFactory()
    request = factory.post('/', data={
        'fileset_name': 'test',
        'command': 'upload'
    })
    request = addFilesToRequest(request, file_list, 'files[]')
    pu = um.ajax(user_id=str(user.id), request=request)


class TestUser(TestCase):
    def setUp(self):
        user = mmodels.User(name="U1")
        user.save()

    def test_user(self):
        u = mmodels.User.objects.all()
        self.assertEqual(u[0].name, "U1")


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
        self.user = mmodels.User(name="UTest")
        self.user.save()
        self.user2 = mmodels.User(name="Utest2")
        self.user2.save()

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
        request = addFilesToRequest(request, self.file_list, 'files[]')
        pu = um.ajax(user_id=str(self.user.id), request=request)
        self.assertEqual(200, pu.status_code, 'code 200 expected')
        ret = json.loads(pu.content)
        if 'success' not in ret['command']:
            self.fail('success not reposted by uploadmanager')

        fileset = mmodels.FileSet.objects.all()[0]
        self.assertEqual(len(self.file_list), len(fileset.files.all()), 'incomplete fileset')
        for f in fileset.files.all():
            cs = f.curveSet
            self.assertEqual(len(cs.curvesData.all()), self.curves_per_file)
            for cd in cs.curvesData.all():
                self.assertEqual(self.curve_length, len(cd.current), f.fileName)
                float(cd.current[3])  # Test "random" element
                float(cd.potential[3])
                float(cd.time[3])
                self.assertTrue(cd.canBeReadBy(self.user))
                self.assertTrue(cd.canBeUpdatedBy(self.user))
                self.assertTrue(cd.isOwnedBy(self.user))
                self.assertFalse(cd.canBeReadBy(self.user2))
                self.assertFalse(cd.canBeUpdatedBy(self.user2))
                self.assertFalse(cd.isOwnedBy(self.user2))
        # TODO: more tests


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
        self.user = mmodels.User(name="UTest")
        self.user.save()
        uploadFile(self.user)
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
