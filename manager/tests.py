from django.test import TestCase
from manager.models import *

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


