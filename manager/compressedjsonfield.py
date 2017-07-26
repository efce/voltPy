import zlib
from base64 import b64decode, b64encode
import json

from django.db import models

# django-jsonfield
from jsonfield import JSONField


class CompressedJSONField(JSONField):
    """
    Django model field that stores JSON data compressed with zlib.
    """
    def from_db_value(self, value, expression, connection, context):#to_python(self, value):
        try:
            value = zlib.decompress(b64decode(value))
        except zlib.error:
            return None
        return json.loads(value)


    def get_db_prep_value(self, value, connection=None, prepared=None):
        value = super(CompressedJSONField, self).get_db_prep_value(value,
                                                                   connection,
                                                                   prepared)
        value = json.dumps(value)
        return b64encode(zlib.compress(value.encode("utf-8"), 9))


# South support
try:
    from south.modelsinspector import add_introspection_rules
    # you may need to modify this regex to match where you install this file
    add_introspection_rules([], ['fields\.CompressedJSONField'])
except ImportError:
    pass
