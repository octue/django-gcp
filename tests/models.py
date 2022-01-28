
from django.db.models import CharField
from rabid_armadillo.models import MyAbstractModel


class Armadillo(MyAbstractModel):
    """
    This is how you test abstract classes in your library without adding concrete models: add the concrete model
     to your test app. You'll need to make the migrations for the test app:
       python manage.py makemigrations tests

    """
    name = CharField(max_length=32)

    class Meta:
        app_label = 'tests'

    def __str__(self):
        # Ensures that the abstract class __str__ method is covered in testing
        return super(Armadillo, self).__str__() + ' ("{}")'.format(self.name)
