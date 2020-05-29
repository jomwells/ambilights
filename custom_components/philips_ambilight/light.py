### Home Assistant Platform to integrate Phillip TVs' Ambilight as a light entity using the JointSpace API ###


import json
import string
import requests
import homeassistant.helpers.config_validation as cv
import voluptuous as vol

from homeassistant.components.light import (ATTR_BRIGHTNESS, LightEntity, PLATFORM_SCHEMA, ATTR_HS_COLOR, ATTR_TRANSITION,
                                            SUPPORT_BRIGHTNESS, SUPPORT_COLOR, SUPPORT_TRANSITION, ATTR_EFFECT, SUPPORT_EFFECT)
from homeassistant.const import (CONF_HOST, CONF_NAME, CONF_USERNAME, CONF_PASSWORD)
from requests.auth import HTTPDigestAuth
from requests.adapters import HTTPAdapter

DEFAULT_DEVICE = 'default'
DEFAULT_HOST = '127.0.0.1'
DEFAULT_USER = 'user'
DEFAULT_PASS = 'pass'
DEFAULT_NAME = 'TV Ambilights'
BASE_URL = 'https://{0}:1926/6/{1}' # for older philps tv's, try changing this to 'http://{0}:1925/1/{1}'
DEFAULT_HUE = 360
DEFAULT_SATURATION = 0
DEFAULT_BRIGHTNESS = 255
TIMEOUT = 5.0
CONNFAILCOUNT = 5


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
	vol.Required(CONF_HOST, default=DEFAULT_HOST): cv.string,
	vol.Required(CONF_USERNAME, default=DEFAULT_USER): cv.string,
	vol.Required(CONF_PASSWORD, default=DEFAULT_PASS): cv.string,
	vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string
})

# these are the names of the effects, change the names in the quotes to change the name displayed on the front-end
EFFECT_MANUAL = "Manual"
EFFECT_STANDARD = "Standard"
EFFECT_NATURAL = "Natural"
EFFECT_IMMERSIVE = "Football"
EFFECT_VIVID = "Vivid"
EFFECT_GAME = "Game"
EFFECT_COMFORT = "Comfort"
EFFECT_RELAX = "Relax"
EFFECT_ADAP_BRIGHTNESS = "Lumina"
EFFECT_ADAP_COLOR = "Colora"
EFFECT_RETRO = "Retro"
EFFECT_SPECTRUM = "Spectrum"
EFFECT_SCANNER = "Scanner"
EFFECT_RHYTHM = "Rhythm"
EFFECT_RANDOM = "Party"
DEFAULT_EFFECT = EFFECT_MANUAL

# this is the list of effects, you can safely remove any effects from the list below to remove them from the front-end
AMBILIGHT_EFFECT_LIST = [EFFECT_MANUAL, EFFECT_STANDARD, EFFECT_NATURAL, EFFECT_IMMERSIVE, EFFECT_VIVID, 
                        EFFECT_GAME, EFFECT_COMFORT, EFFECT_RELAX, EFFECT_ADAP_BRIGHTNESS, EFFECT_ADAP_COLOR,
                        EFFECT_RETRO, EFFECT_SPECTRUM, EFFECT_SCANNER, EFFECT_RHYTHM, EFFECT_RANDOM]

def setup_platform(hass, config, add_devices, discovery_info=None):
	name = config.get(CONF_NAME)
	host = config.get(CONF_HOST)
	user = config.get(CONF_USERNAME)
	password = config.get(CONF_PASSWORD)
	add_devices([Ambilight(name, host, user, password)])

OLD_STATE = [DEFAULT_HUE, DEFAULT_SATURATION, DEFAULT_BRIGHTNESS, DEFAULT_EFFECT]

class Ambilight(LightEntity):

    def __init__(self, name, host, user, password):
        self._name = name
        self._host = host
        self._user = user
        self._password = password
        self._state = None
        self._connfail = 0
        self._brightness = None
        self._hs = None
        self._available = False
        self._effect = None
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
    def supported_features(self):
        return SUPPORT_BRIGHTNESS | SUPPORT_COLOR | SUPPORT_EFFECT

    @property
    def effect_list(self):
        return AMBILIGHT_EFFECT_LIST

    @property
    def brightness(self):
        return self._brightness

    @property
    def hs_color(self):
        return self._hs

    @property
    def effect(self):
        return self._effect

    @property
    def should_poll(self):
        return True

    def turn_on(self, **kwargs):
        if ATTR_TRANSITION in kwargs:
            # Here we save current color and brightness
            convertedHue_old = int(self._hs[0]*(255/360))
            convertedBrightness_old = self._brightness
            if ATTR_BRIGHTNESS in kwargs:
                convertedBrightness = kwargs[ATTR_BRIGHTNESS]
            else:
                convertedBrightness = self._brightness
            self._hs = kwargs[ATTR_HS_COLOR] if (ATTR_HS_COLOR in kwargs) else self._hs
            convertedHue = int(self._hs[0]*(255/360))
            convertedSaturation = int(self._hs[1]*(255/100))
            hue_addorsubst = 1 if (convertedHue_old < convertedHue) else -1
            bright_addorsubst = 1 if (convertedBrightness_old < convertedBrightness) else -1
            # Now we start transition from old color/brightness to new color and brightness. Loop until match.
            while convertedHue_old != convertedHue or convertedBrightness_old != convertedBrightness:
                convertedHue_old = (convertedHue_old + hue_addorsubst) if convertedHue_old != convertedHue else convertedHue
                convertedBrightness_old = (convertedBrightness_old + bright_addorsubst) if convertedBrightness_old != convertedBrightness else convertedBrightness
                self._postReq('ambilight/currentconfiguration',{"styleName":"FOLLOW_COLOR","isExpert":True,"algorithm":"MANUAL_HUE",
                "colorSettings":{"color":{"hue":convertedHue_old,"saturation":convertedSaturation,"brightness":convertedBrightness_old},
                "colorDelta":{"hue":0,"saturation":0,"brightness":0},"speed":255}} )
            self.getState()
        elif ATTR_HS_COLOR in kwargs:
            self._hs = kwargs[ATTR_HS_COLOR]
            convertedHue = int(self._hs[0]*(255/360))
            convertedSaturation = int(self._hs[1]*(255/100))
            if ATTR_BRIGHTNESS in kwargs:
                convertedBrightness = kwargs[ATTR_BRIGHTNESS]
            else:
                convertedBrightness = self._brightness
            self._postReq('ambilight/currentconfiguration',{"styleName":"FOLLOW_COLOR","isExpert":True,"algorithm":"MANUAL_HUE",
            "colorSettings":{"color":{"hue":convertedHue,"saturation":convertedSaturation,"brightness":convertedBrightness},
            "colorDelta":{"hue":0,"saturation":0,"brightness":0},"speed":255}} )

        elif ATTR_BRIGHTNESS in kwargs:
            # use this section instead if you cannot change the brightness without the bulb changing colour
            # (brightness commands are limited to integer values 1:10)
            #convertedBrightness = int(10*(kwargs[ATTR_BRIGHTNESS])/255)
            #self._postReq('menuitems/settings/update', "values": [{"value": {"Nodeid": 2131230769, "Controllable": "true", "Available": "true", "string_id": "Brightness", "data": {"value": convertedBrightness}}}]} )
            # and comment out all of the following
            
            convertedBrightness = kwargs[ATTR_BRIGHTNESS]
            self._postReq('ambilight/currentconfiguration',{"styleName":"FOLLOW_COLOR","isExpert":True,"algorithm":"MANUAL_HUE",
            "colorSettings":{"color":{"hue":int(self._hs[0]*(255/360)),"saturation":int(self._hs[1]*(255/100)),
            "brightness":convertedBrightness},"colorDelta":{"hue":0,"saturation":0,"brightness":0},"speed":255}} )

        elif ATTR_EFFECT in kwargs:
            effect = kwargs[ATTR_EFFECT]
            self.set_effect(effect)

        else:
            if OLD_STATE[3] == EFFECT_MANUAL:
                self._postReq('ambilight/currentconfiguration',{"styleName":"FOLLOW_COLOR","isExpert":True,"algorithm":"MANUAL_HUE",
                "colorSettings":{"color":{"hue":int(OLD_STATE[0]*(255/360)),"saturation":int(OLD_STATE[1]*(255/100)),
                "brightness":OLD_STATE[2]},"colorDelta":{"hue":0,"saturation":0,"brightness":0},"speed":255}} )
            else: 
                effect = self._effect
                self.set_effect(effect)

    def turn_off(self, **kwargs):
        global OLD_STATE
        OLD_STATE = [self._hs[0], self._hs[1], self._brightness, self._effect]
        self._postReq('ambilight/power', {'power':'Off'})
        self._state = False
		
    def getState(self):
        fullstate = self._getReq('ambilight/currentconfiguration')
        if fullstate:
            self._available = True
            styleName = fullstate['styleName']
            if styleName:
                if styleName == 'FOLLOW_COLOR':
                    isExpert = fullstate['isExpert']
                    if isExpert == True:
                        self._state = True
                        colorSettings = fullstate['colorSettings']
                        color = colorSettings['color']
                        hue = color['hue']
                        saturation = color['saturation']
                        bright = color['brightness']
                        self._hs = (hue*(360/255),saturation*(100/255))
                        self._brightness = bright
                        self._effect = EFFECT_MANUAL
                    else:
                        self._hs = (DEFAULT_HUE, DEFAULT_SATURATION)
                        self._brightness = DEFAULT_BRIGHTNESS

                elif styleName == 'FOLLOW_VIDEO':
                    self._state = True
                    self._hs = (DEFAULT_HUE, DEFAULT_SATURATION)
                    self._brightness = DEFAULT_BRIGHTNESS
                    effect = fullstate['menuSetting']
                    if effect == "STANDARD":
                        self._effect = EFFECT_STANDARD
                    elif effect == "NATURAL":
                        self._effect = EFFECT_NATURAL
                    elif effect == "IMMERSIVE":
                        self._effect = EFFECT_IMMERSIVE
                    elif effect == "VIVID":
                        self._effect = EFFECT_VIVID
                    elif effect == "GAME":
                        self._effect = EFFECT_GAME
                    elif effect == "COMFORT":
                        self._effect = EFFECT_COMFORT
                    elif effect == "RELAX":
                        self._effect = EFFECT_RELAX
                    
                elif styleName == 'FOLLOW_AUDIO':
                    self._state = True
                    self._hs = (DEFAULT_HUE, DEFAULT_SATURATION)
                    self._brightness = DEFAULT_BRIGHTNESS
                    effect = fullstate['menuSetting']
                    if effect == "VU_METER":
                        self._effect = EFFECT_RETRO
                    elif effect == "ENERGY_ADAPTIVE_BRIGHTNESS":
                        self._effect = EFFECT_ADAP_BRIGHTNESS
                    elif effect == "ENERGY_ADAPTIVE_COLORS":
                        self._effect = EFFECT_ADAP_COLOR  
                    elif effect == "SPECTUM_ANALYSER":
                        self._effect = EFFECT_SPECTRUM
                    elif effect == "KNIGHT_RIDER_ALTERNATING":
                        self._effect = EFFECT_SCANNER
                    elif effect == "RANDOM_PIXEL_FLASH":
                        self._effect = EFFECT_RHYTHM
                    elif effect == "MODE_RANDOM":
                        self._effect = EFFECT_RANDOM

        else:
            self._available = False
            self._state = False

    def update(self):
        self.getState()

    def set_effect(self, effect):
        if effect:
            if effect == EFFECT_MANUAL:
                self._postReq('ambilight/currentconfiguration',{"styleName":"FOLLOW_COLOR","isExpert":True,"algorithm":"MANUAL_HUE",
                "colorSettings":{"color":{"hue":int(OLD_STATE[0]*(255/360)),"saturation":int(OLD_STATE[1]*(255/100)),
                "brightness":OLD_STATE[2]},"colorDelta":{"hue":0,"saturation":0,"brightness":0},"speed":255}} )
                self._hs = (OLD_STATE[0], OLD_STATE[1])
                self._brightness = OLD_STATE[2]
            elif effect == EFFECT_STANDARD:
                self._postReq('ambilight/currentconfiguration', {"styleName":"FOLLOW_VIDEO","isExpert":False,"menuSetting":"STANDARD"})
            elif effect == EFFECT_NATURAL:
                self._postReq('ambilight/currentconfiguration', {"styleName":"FOLLOW_VIDEO","isExpert":False,"menuSetting":"NATURAL"})
            elif effect == EFFECT_IMMERSIVE:
                self._postReq('ambilight/currentconfiguration', {"styleName":"FOLLOW_VIDEO","isExpert":False,"menuSetting":"IMMERSIVE"})
            elif effect == EFFECT_VIVID:
                self._postReq('ambilight/currentconfiguration', {"styleName":"FOLLOW_VIDEO","isExpert":False,"menuSetting":"VIVID"})
            elif effect == EFFECT_GAME:
                self._postReq('ambilight/currentconfiguration', {"styleName":"FOLLOW_VIDEO","isExpert":False,"menuSetting":"GAME"})
            elif effect == EFFECT_COMFORT:
                self._postReq('ambilight/currentconfiguration', {"styleName":"FOLLOW_VIDEO","isExpert":False,"menuSetting":"COMFORT"})
            elif effect == EFFECT_RELAX:
                self._postReq('ambilight/currentconfiguration', {"styleName":"FOLLOW_VIDEO","isExpert":False,"menuSetting":"RELAX"})
            elif effect == EFFECT_ADAP_BRIGHTNESS:
                self._postReq('ambilight/currentconfiguration', {"styleName":"FOLLOW_AUDIO","isExpert":False,"menuSetting":"ENERGY_ADAPTIVE_BRIGHTNESS"})
            elif effect == EFFECT_ADAP_COLOR:
                self._postReq('ambilight/currentconfiguration', {"styleName":"FOLLOW_AUDIO","isExpert":False,"menuSetting":"ENERGY_ADAPTIVE_COLORS"})
            elif effect == EFFECT_RETRO:
                self._postReq('ambilight/currentconfiguration', {"styleName":"FOLLOW_AUDIO","isExpert":False,"menuSetting":"VU_METER"})
            elif effect == EFFECT_SPECTRUM:
                self._postReq('ambilight/currentconfiguration', {"styleName":"FOLLOW_AUDIO","isExpert":False,"menuSetting":"SPECTRUM_ANALYSER"})
            elif effect == EFFECT_SCANNER:
                self._postReq('ambilight/currentconfiguration', {"styleName":"FOLLOW_AUDIO","isExpert":False,"menuSetting":"KNIGHT_RIDER_ALTERNATING"})
            elif effect == EFFECT_RHYTHM:
                self._postReq('ambilight/currentconfiguration', {"styleName":"FOLLOW_AUDIO","isExpert":False,"menuSetting":"RANDOM_PIXEL_FLASH"})
            elif effect == EFFECT_RANDOM:
                self._postReq('ambilight/currentconfiguration', {"styleName":"FOLLOW_AUDIO","isExpert":False,"menuSetting":"MODE_RANDOM"})

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
            if resp.status_code == 200:
                return True
            else:
                return False
        except requests.exceptions.RequestException as err:
            self._connfail = CONNFAILCOUNT
            self.on = False
            return False
