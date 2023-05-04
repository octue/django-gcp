import logging
from django.forms.fields import JSONField

from .widgets import CloudObjectWidget


logger = logging.getLogger(__name__)


class CloudObjectFormField(JSONField):
    """Overrides the forms.JSONField with a widget to handle file selection and upload"""

    empty_value = None
    widget = CloudObjectWidget


# from django.forms import FileField
# from django.core.files.uploadedfile import UploadedFile
# from django.core.exceptions import ValidationError

# from .direct_upload_widgets import DirectUploadWidget
# class DirectUploadedFile(UploadedFile):
#     """Represents a file that was uploaded direct to bucket"""


# class DirectUploadFormField(FileField):
#     """Overrides the usual forms.FileField with a widget that handles direct uploads"""

#     widget = DirectUploadWidget

#     def to_python(self, data):
#         """Override the FileField to_python method to accept data as a string file name"""

#         if data in self.empty_values:
#             return None

#         # A file was attached as an indirect upload (the normal way)
#         if isinstance(data, UploadedFile):
#             try:
#                 file_name = data.name
#                 file_size = data.size
#             except AttributeError:
#                 # pylint: disable=raise-missing-from
#                 raise ValidationError(self.error_messages["invalid"], code="invalid")
#                 # pylint: enable=raise-missing-from

#             if not self.allow_empty_file and not file_size:
#                 raise ValidationError(self.error_messages["empty"], code="empty")

#         # A file was uploaded direct-to-bucket, data only contains its name
#         elif isinstance(data, str):
#             file_name = data
#             file_size = None
#             data = DirectUploadedFile(name=file_name, size=None)
#             if not self.allow_empty_file:
#                 logger.warning(
#                     "`allow_empty_file` is set but file has been directly uploaded. Cannot validate emptiness of file."
#                 )

#         else:
#             raise ValueError(f"Unknown data of class {data.__class__}: {data}")
#         print("FILE NAME", file_name)
#         if self.max_length is not None and len(file_name) > self.max_length:
#             params = {"max": self.max_length, "length": len(file_name)}
#             raise ValidationError(self.error_messages["max_length"], code="max_length", params=params)

#         if not file_name:
#             raise ValidationError(self.error_messages["invalid"], code="invalid")

#         return data
