from django.test import TestCase

from rabid_armadillo.models import MyModel


class MyModelTestCase(TestCase):
    """ "Normal" synchronous django tests to ensure your models / rest API / Whatever works correctly
    """

    def test_something(self):
        """ Test that something happens
        """
        MyModel()
