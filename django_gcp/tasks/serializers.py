from datetime import datetime
import json

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.fields.files import FieldFile

DEFAULT_TIMEZONE = getattr(settings, "TIMEZONE", "UTC")


def assure_tz(dt, tz=DEFAULT_TIMEZONE):
    """Add timezone information to a datetime if not already present"""
    if not dt:
        return dt
    if not dt.tzinfo:
        dt = tz.localize(dt)
    return dt


class JSONEncoder(DjangoJSONEncoder):
    """A JSON encoder with additional serialiation options
    This encoder serializes:
     - `datetime`s as isoformatted, timezone-aware strings
     - django `FieldFile`s by their URL string
     - python `set`s as lists
    """

    def default(self, o):
        """Override default serialization to apply isoformat to timezones"""
        if o is None:
            return None
        if isinstance(o, datetime):
            value = assure_tz(o.astimezone())
            return value.isoformat()
        if issubclass(o.__class__, FieldFile):
            return o.url if bool(o) else None
        if isinstance(o, set):
            return list(o)
        return super().default(o)


def serialize(value):
    return json.dumps(value, cls=JSONEncoder)


def deserialize(value):
    return json.loads(value)
