import json
from datetime import datetime, date

class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime and date objects"""
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)

def json_dumps(data, **kwargs):
    """Utility for JSON serialization with DateTimeEncoder and standard defaults"""
    kwargs.setdefault('cls', DateTimeEncoder)
    kwargs.setdefault('separators', (',', ':'))
    kwargs.setdefault('sort_keys', True)
    return json.dumps(data, **kwargs)
