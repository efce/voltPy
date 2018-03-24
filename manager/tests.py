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
        if not test_file.is_file():
            raise 
        with open(test_file.absolute(), "rb") as ufile:
            bytefile = io.BytesIO(ufile.read())
            fsize = ufile.tell()
            fname = ufile.name
        inmemoryfile = InMemoryUploadedFile(bytefile, 'file', fname, None, fsize, None)
        _filelist.append(inmemoryfile)
    request.FILES.setlist(post_name, _filelist)
    return request


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

    def setUp(self):
        self.user = mmodels.User(name="UTest")
        self.user.save()

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
        assert pu.status_code == 200
        ret = json.loads(pu.content)
        if 'success' not in ret['command']:
            self.fail('success not reposted by uploadmanager')

        fileset = mmodels.FileSet.objects.all()[0]
        assert len(fileset.files.all()) == len(self.file_list)
        for f in fileset.files.all():
            cs = f.curveSet
            assert len(cs.curvesData.all()) == 24
            # TODO: more tests

        #fid = pu.getFileId()
        #cf = mmodels.CurveFile.objects.get(id=fid)
        #self.assertEqual(cf.name, testname)
        #self.assertEqual(cf.comment, testcomment)
        #c = mmodels.Curve.objects.all()
        #self.assertEqual(len(c), 24) #there should be 24 curves in file
        #ci = mmodels.CurveIndex.objects.all()
        #self.assertEqual(len(ci), 24)
        #cd = mmodels.CurveData.objects.all()
        #self.assertEqual(len(cd), 24)
        #float(cd.yVector[3])
        #float(cd.xVector[3])


class TestMethodManager(TestCase):
    testmethod = """
import manager.methodmanager as mm

class TestMethod(mm.ProcessingMethod):
    _operations = [
    ]

    def __str__(self):
        return "TestMethod"

    def finalize(self, user):
        self.model.customData['FINALIZED'] = user.id
        self.model.step = None
        self.model.completed = True
        self.model.save()

    def getInfo(self, request, user):
        return { 'head': '', 'body': '' }

main_class = TestMethod
    """

    def setUp(self):
        self.user = mmodels.User(name="UTest")
        self.user.save()
        filepath = "./pb_4mgL_CTAB.volt"
        test_file = Path(filepath)
        if not test_file.is_file():
            self.fail("test file: pb_4mgL_CTAB.volt is missing")
        ufile = open(test_file.absolute(), "rb")
        pu = mpu.ProcessUpload(self.user, ufile, 'name', 'comment')
        fid = pu.getFileId()
        cs = mmodels.CurveSet(
            owner=self.user,
            name='test cs',
            date=timezone.now(),
            locked=False,
            deleted=False
        )
        cs.save()
        self.curveset = cs
        for cd in mmodels.CurveData.objects.all():
            cs.curveData.add(cd)

        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.methods_path = os.path.join(BASE_DIR, 'manager', 'methods')
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
        print(mema.methods)
        self.assertEqual(mema.methods['processing']['TestMethod'].__name__, 'TestMethod')

    def test_methods_usage(self):
        p = mmodels.Processing(
            owner=self.user,
            curveSet=self.curveset,
            date=timezone.now(),
            customData={},
            name='PROC',
            method='TestMethod',
            step=0,
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
