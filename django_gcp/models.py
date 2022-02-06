import logging
from django.db import models
from django.utils.translation import ugettext_lazy as _


logger = logging.getLogger(__name__)


class MyAbstractModel(models.Model):
    """An example abstract model from the rabid-armadillo template"""

    slug = models.SlugField(
        verbose_name=_("slug"), allow_unicode=False, unique=True, max_length=255, help_text=_("A slug.")
    )

    class Meta:
        """Metaclass data for MyAbstractModel"""

        abstract = True


# class MyModel(MyAbstractModel):
#     """An example concrete model from the rabid-armadillo template
#     Commented out to avoid accidentally generating migrations for it
#     """

#     name = models.CharField(max_length=32, null=True, blank=True)

#     class Meta:
#         verbose_name = _("My Model")
#         verbose_name_plural = _("My Models")
