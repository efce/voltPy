from django.test import TestCase
from manager.models import *
from manager.processupload import *

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
        user = User(name="U1")
        user.save()

    def test_user(self):
        u = User.objects.all()
        self.assertEqual(u[0].name, "U1")

class TestFileUpload(TestCase):
    def setUp(self):
        self.user = User(name="UTest")
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
        pu = ProcessUpload(self.user, ufile, testname, testcomment)
        fid = pu.getFileId()
        cf = CurveFile.objects.get(id=fid)
        self.assertEqual(cf.name, testname)
        self.assertEqual(cf.comment, testcomment)
        c = Curve.objects.all()
        self.assertEqual(len(c), 24) #there should be 24 curves in file
        ci = CurveIndex.objects.all()
        self.assertEqual(len(ci), 24)
        cd = CurveData.objects.all()
        self.assertEqual(len(cd), 24)
