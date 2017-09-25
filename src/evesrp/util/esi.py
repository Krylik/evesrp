from flask import current_app
import requests


class EntityLookup(object):
    _url = None

    def __init__(self, entity_id, requests_session=None):
        self._dict = None
        self._entity_id = entity_id
        if requests_session is None:
            try:
                self.requests_session = current_app.requests_session
            except (AttributeError, RuntimeError):
                self.requests_session = requests.Session()
        else:
            self.requests_session = requests_session

    def __getitem__(self, key):
        if not self._dict:
            resp = self.requests_session.get(
                self.__class__._url.format(
                    self._entity_id))
            if resp.status_code == 200:
                self._dict = resp.json()
            else:
                raise KeyError('An error occurred querying the esi api')
        if key in self._dict:
            return self._dict[key]
        else:
            raise KeyError('{} data does not contain {}'.format(
                self.__class__, key))


class CharacterLookup(EntityLookup):
    _url = 'https://esi.tech.ccp.is/latest/characters/{}/'

    @property
    def name(self):
        return self['name']


class AllianceLookup(EntityLookup):
    _url = 'https://esi.tech.ccp.is/latest/alliances/{}/'

    @property
    def name(self):
        return self['alliance_name']


class CorporationLookup(EntityLookup):
    _url = 'https://esi.tech.ccp.is/latest/corporations/{}/'

    @property
    def name(self):
        return self['corporation_name']


class ItemLookup(EntityLookup):
    _url = 'https://esi.tech.ccp.is/latest/universe/types/{}/'

    @property
    def name(self):
        return self['name']
