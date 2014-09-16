import arrow
import cPickle
import datetime
from enum import Enum
from marrow.util.bunch import Bunch
from marrow.util.convert import boolean, number, array
from flask import current_app
from relaxml import xml
import requests
from newauth.models import redis


class TooManyAPIErrors(Exception):

    def __init__(self, key_id):
        message = "Got too many API errors in the last minute for key #{}.".format(key_id)
        Exception.__init__(self, message)


class APIKeyDisabled(Exception):

    def __init__(self, key_id):
        message = "APIKey #{} disabled.".format(key_id)
        Exception.__init__(self, message)


class AuthenticationException(Exception):

    def __init__(self, key_id):
        message = "Authentication error for key #{}".format(key_id)
        Exception.__init__(self, message)


def bunchify(data, name=None):
    if isinstance(data, Bunch):
        return data

    if isinstance(data, list):
        if name == 'rowset':  # we unpack these into a dictionary based on name
            return Bunch({i['name']: bunchify(i, 'rowset') for i in data})

        return [bunchify(i) for i in data]

    if isinstance(data, dict):
        data = data.copy()

        if name == 'row' and 'row' in data:
            # Special case of CCP's silly key:value text.
            pass

        if name and name in data and not data.get(name, '').strip():
            data.pop(name)

        if name == 'rowset' and 'name' in data:
            data.pop('name')

        if len(data) == 1 and isinstance(data.values()[0], dict):
            return bunchify(data.values()[0], data.keys()[0])

        result = Bunch({
                k: bunchify(
                        [v] if k in ('row', ) and not isinstance(v, list) else v,
                        k
                    ) for k, v in data.iteritems() if k != 'rowset'
            })

        if 'rowset' in data:
            rowset = bunchify(data['rowset'] if isinstance(data['rowset'], list) else [data['rowset']], 'rowset')
            result.update(rowset)

        if name == 'rowset':  # rowsets always contain rows, even if there are no results
            result.setdefault('row', [])

        return result

    if isinstance(data, str):
        data = data.decode('utf-8')

    if isinstance(data, (str, unicode)):
        try:
            return number(data)
        except ValueError:
            pass

        try:
            return boolean(data)
        except ValueError:
            pass

        if ',' in data and (name in ('key', 'columns') or ' ' not in data):
            return array(data)

    return data


class EveAPIQuery(object):
    """EveAPI Query object."""

    def __init__(self, public=False, api_key=None, key_id=None, vcode=None, base="https://api.eveonline.com/"):
        from newauth.models import APIKey, db
        self.base = base
        self.api_key = None
        self.session = requests.Session()
        if public:
            self.public = True
        if api_key and isinstance(api_key, APIKey):
            self.init_with_model(api_key)
        else:
            self.init_classic(key_id, vcode)

    def init_with_model(self, api_key):
        self.public = False
        if api_key.last_error_on:
            if api_key.error_count > 3 and (api_key.last_error_on - datetime.datetime.utcnow()).total_seconds() < 60.0:
                raise TooManyAPIErrors(api_key.key_id)
        if api_key.disabled:
            raise APIKeyDisabled(api_key.key_id)
        self.api_key = api_key
        self.key_id = api_key.key_id
        self.vcode = api_key.vcode
        self.session.params = {'keyID': self.key_id, 'vCode': self.vcode}

    def init_classic(self, key_id, vcode):
        self.public = False
        self.key_id = key_id
        self.vcode = vcode
        self.session.params = {'keyID': self.key_id, 'vCode': self.vcode}

    def get(self, call, **kwargs):
        from newauth.models import APIKey, db
        if self.key_id and self.vcode:
            cache_key = hash((self.base, call, self.key_id, self.vcode, frozenset(kwargs.items())))
        else:
            cache_key = hash((self.base, call, frozenset(kwargs.items())))
        cached_data = redis.get(cache_key)
        if cached_data:
            cached_data = cPickle.loads(cached_data)
            if arrow.utcnow() < cached_data[0]:
                return cached_data[1]
        req = None
        try:
            req = self.session.get(self.base + call + '.xml.aspx', params=kwargs)
            req.raise_for_status()
        except requests.exceptions.RequestException as e:
            if req and req.status_code == requests.codes['forbidden']:
                raise AuthenticationException(self.key_id)
            raise e
        if req.status_code != 200:
            if req.status_code == requests.codes['not_found']:
                raise Exception("{} is not available on the API server (404)".format(call.value))
            elif req.status_code == requests.codes['forbidden']:
                if self.api_key and self.api_key.id:
                    self.api_key.disabled = True
                    db.session.add(self.api_key)
                    db.session.commit()
                raise AuthenticationException(self.key_id)
            else:
                raise Exception("Eve API server exception.")
        request_data = req.text

        prefix, _, data = req.text.partition('\n')
        if prefix.strip() != "<?xml version='1.0' encoding='UTF-8'?>":
            raise Exception("Data returned doesn't seem to be XML!")

        if isinstance(data, unicode):
            data = data.encode('UTF-8')

        data = xml(data)['eveapi']
        result = bunchify(data['result'], 'result')
        data = Bunch(data)

        if len(result) == 1:
            result = getattr(result, result.keys())[0]
        redis.set(cache_key, cPickle.dumps((arrow.get(data.cachedUntil), result), -1))
        redis.expire(cache_key, 60 * 60 * 6)
        return result

