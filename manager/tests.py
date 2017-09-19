import os
from django.test import TestCase
import manager.models as mmodels
import manager.processupload as mpu
import manager.methodmanager as mm
from django.utils import timezone

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

class TestUser(TestCase):
    def setUp(self):
        user = mmodels.User(name="U1")
        user.save()

    def test_user(self):
        u = mmodels.User.objects.all()
        self.assertEqual(u[0].name, "U1")

class TestFileUpload(TestCase):
    def setUp(self):
        self.user = mmodels.User(name="UTest")
        self.user.save()

    def test_file_upload(self):
        filepath = "./pb_4mgL_CTAB.volt"
        from pathlib import Path
        test_file = Path(filepath)
        if not test_file.is_file():
            self.fail("test file: pb_4mgL_CTAB.volt is missing")

        ufile = open(test_file.absolute(), "rb")

        testname = "tęśß ńąµę"
        testcomment = "ßęśß ćóµµęńß"
        pu = mpu.ProcessUpload(self.user, ufile, testname, testcomment)
        fid = pu.getFileId()
        cf = mmodels.CurveFile.objects.get(id=fid)
        self.assertEqual(cf.name, testname)
        self.assertEqual(cf.comment, testcomment)
        c = mmodels.Curve.objects.all()
        self.assertEqual(len(c), 24) #there should be 24 curves in file
        ci = mmodels.CurveIndex.objects.all()
        self.assertEqual(len(ci), 24)
        cd = mmodels.CurveData.objects.all()
        self.assertEqual(len(cd), 24)

class TestMethodManager(TestCase):
    testmethod="""
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
        from pathlib import Path
        test_file = Path(filepath)
        if not test_file.is_file():
            self.fail("test file: pb_4mgL_CTAB.volt is missing")
        ufile = open(test_file.absolute(), "rb")
        pu = mpu.ProcessUpload(self.user, ufile, 'name', 'comment')
        fid = pu.getFileId()
        cs = mmodels.CurveSet(
            owner = self.user,
            name = 'test cs',
            date = timezone.now(),
            locked = False,
            deleted = False
        )
        cs.save()
        self.curveset = cs
        for cd in mmodels.CurveData.objects.all():
            cs.usedCurveData.add(cd)

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
            date = timezone.now(),
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
