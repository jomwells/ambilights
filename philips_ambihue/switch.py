import json
import string
import requests
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.switch import (
    DOMAIN, PLATFORM_SCHEMA, SwitchDevice, ENTITY_ID_FORMAT)
from homeassistant.const import (CONF_HOST, CONF_NAME, CONF_USERNAME, CONF_PASSWORD, STATE_OFF, STATE_STANDBY, STATE_ON)
from requests.auth import HTTPDigestAuth
from requests.adapters import HTTPAdapter

DEFAULT_DEVICE = 'default'
DEFAULT_HOST = '127.0.0.1'
DEFAULT_USER = 'user'
DEFAULT_PASS = 'pass'
DEFAULT_NAME = 'Ambiight+hue'
BASE_URL = 'https://{0}:1926/6/{1}' # for older philps tv's, try changing this to 'http://{0}:1925/1/{1}'
TIMEOUT = 5.0
CONNFAILCOUNT = 5

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
	vol.Required(CONF_HOST, default=DEFAULT_HOST): cv.string,
	vol.Required(CONF_USERNAME, default=DEFAULT_USER): cv.string,
	vol.Required(CONF_PASSWORD, default=DEFAULT_PASS): cv.string,
	vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string
})

def setup_platform(hass, config, add_devices, discovery_info=None):
	name = config.get(CONF_NAME)
	host = config.get(CONF_HOST)
	user = config.get(CONF_USERNAME)
	password = config.get(CONF_PASSWORD)
	add_devices([AmbiHue(name, host, user, password)])

class AmbiHue(SwitchDevice):

    def __init__(self, name, host, user, password):
        self._name = name
        self._host = host
        self._user = user
        self._password = password
        self._state = False
        self._connfail = 0
        self._available = False
        self._session = requests.Session()
        self._session.mount('https://', HTTPAdapter(pool_connections=1))

    @property
    def name(self):
        return self._name

    @property
    def is_on(self):
        return self._state

    @property
    def available(self):
        return self._available

    @property
    def should_poll(self):
        return True


    def turn_on(self, **kwargs):
        self._postReq('menuitems/settings/update', {"values":[{"value":{"Nodeid":2131230774,"Controllable":"true","Available":"true","data":{"value":"true"}}}]} )
        self._state = True

    def turn_off(self, **kwargs):
        self._postReq('menuitems/settings/update', {"values":[{"value":{"Nodeid":2131230774,"Controllable":"true","Available":"true","data":{"value":"false"}}}]} )
        self._state = False

    def getState(self):
        fullstate = self._postReq('menuitems/settings/current', {'nodes':[{'nodeid':2131230774}]})
        if fullstate:
            self._available = True
            ahstat = fullstate['values'][0]['value']['data']['value']
            if ahstat == True:
                self._state = True
            else:
                self._state = False
        else:
            self._available = False
            self._state = False

    def update(self):
        self.getState()

    def _getReq(self, path):
        try:
            if self._connfail:
                self._connfail -= 1
                return None
            resp = self._session.get(BASE_URL.format(self._host, path), verify=False, auth=HTTPDigestAuth(self._user, self._password), timeout=TIMEOUT)
            self.on = True
            return json.loads(resp.text)
        except requests.exceptions.RequestException as err:
            self._connfail = CONNFAILCOUNT
            self.on = False
            return None

    def _postReq(self, path, data):
        try:
            if self._connfail:
                self._connfail -= 1
                return False
            resp = self._session.post(BASE_URL.format(self._host, path), data=json.dumps(data), verify=False, auth=HTTPDigestAuth(self._user, self._password), timeout=TIMEOUT)
            self.on = True
            return json.loads(resp.text)
        except requests.exceptions.RequestException as err:
            self._connfail = CONNFAILCOUNT
            self.on = False
            return False
