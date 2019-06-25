import json, string, requests
from yeelight import *
import time, random, urllib3
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.switch import (
    DOMAIN, PLATFORM_SCHEMA, SwitchDevice, ENTITY_ID_FORMAT)
from homeassistant.const import (CONF_HOST, CONF_NAME, CONF_USERNAME, CONF_PASSWORD, CONF_ADDRESS, CONF_DISPLAY_OPTIONS, STATE_OFF, STATE_STANDBY, STATE_ON)
from requests.auth import HTTPDigestAuth
from requests.adapters import HTTPAdapter

DEFAULT_DEVICE = 'default'
DEFAULT_HOST = '127.0.0.1'
DEFAULT_USER = 'user'
DEFAULT_PASS = 'pass'
DEFAULT_NAME = 'Ambiights+Yeelight'
DEFAULT_DISPLAY_OPTIONS = 'top'
BASE_URL = 'https://{0}:1926/6/{1}' # for older philps tv's, try changing this to 'http://{0}:1925/1/{1}'
TIMEOUT = 5.0 # get/post request timeout with tv
CONNFAILCOUNT = 5 # number of get/post attempts
DEFAULT_RGB_COLOR = [255,255,255] # default colour for bulb when dimmed in game mode (and incase of failure)  

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
	vol.Required(CONF_HOST, default=DEFAULT_HOST): cv.string,
	vol.Required(CONF_USERNAME, default=DEFAULT_USER): cv.string,
	vol.Required(CONF_PASSWORD, default=DEFAULT_PASS): cv.string,
	vol.Required(CONF_ADDRESS, default=DEFAULT_HOST): cv.string,
	vol.Optional(CONF_DISPLAY_OPTIONS, default=DEFAULT_DISPLAY_OPTIONS): cv.string,
	vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string
})

def setup_platform(hass, config, add_devices, discovery_info=None):
	name = config.get(CONF_NAME)
	tvip = config.get(CONF_HOST)
	user = config.get(CONF_USERNAME)
	password = config.get(CONF_PASSWORD)
	bulbip = config.get(CONF_ADDRESS)
	option = config.get(CONF_DISPLAY_OPTIONS)
	add_devices([AmbiHue(name, tvip, bulbip, user, password, option)])

class AmbiHue(SwitchDevice):

    def __init__(self, name, tvip, bulbip, user, password, option):
        self._name = name
        self._bulbip = bulbip
        self._tvip = tvip
        self._user = user
        self._password = password
        self._position = option
        self._state = False
        self._powerstate = False
        self._connfail = 0
        self._available = False
        self._session = requests.Session()
        self._session.mount('https://', HTTPAdapter(pool_connections=1))
        self._bulb = Bulb(bulbip)

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
        self.connect()
        self.update()
        if self._powerstate == 'off':
            self._bulb.turn_on()
        self._bulb.start_music() # for updates to be quick enough for this to work, the 'music mode' must be enabled (see Yeelight API)
        self._follow = True
        self._state = True
        self.follow_tv(self._position, 0.05) # 0.05ms is the 'sleep' time between refresh cycles

    def turn_off(self, **kwargs):
        self._follow = False
        self.connect()
        self._bulb.stop_music() # disables (more intensive) music mode afterward
        self._state = False

    def getState(self):
        powerstate = self._bulb.get_properties()['power']
        musicstate = self._bulb.get_properties()['music_on']
        return powerstate, musicstate

    def update(self):
        self.connect()
        self._powerstate, musicstate = self.getState()
        if int(musicstate) == 1:
            self._state = True
        else:
            self._state = False

    def connect(self):
        try:
            properties = self._bulb.get_properties()
            if properties:
                self._available = True
            else:
                self._available = False
        except:
            print("Failed to find bulb, trying again in 2s")
            time.sleep(2)
    
    def follow_tv(self, position, sleep): 
        while self._follow == True: # main loop for updating the bulb
            try:
                ambiSetting = self._getReq('ambilight/currentconfiguration') # determines the effect/follow style of the ambilights
                if ambiSetting['styleName'] == "FOLLOW_VIDEO":
                    currentstate = self._getReq('ambilight/measured') # uses pre-processing r,g,b values from tv (see: http://jointspace.sourceforge.net/projectdata/documentation/jasonApi/1/doc/API-ambilight.html)
                else:
                    currentstate = self._getReq('ambilight/processed') # uses post-processing r,g,b values from tv (allows yeelight bulb to follow tv's algorithms such as the follow audio effects and colours set by home assistant)
                layer1 = currentstate['layer1']
                
                # below calulates different average r,g,b values to send to the lamp
                # see: http://jointspace.sourceforge.net/projectdata/documentation/jasonApi/1/doc/API-Method-ambilight-measured-GET.html
                # etc in http://jointspace.sourceforge.net/projectdata/documentation/jasonApi/1/doc/API.html
                
                
                if position == 'top-middle-average': # 'display_options' value given in home assistant 
                    pixels = layer1['top'] # for tv topology see http://jointspace.sourceforge.net/projectdata/documentation/jasonApi/1/doc/API-Method-ambilight-topology-GET.html
                    pixel3 = str((int(len(pixels)/2)-1)) # selects pixels
                    pixel4 = str(int(len(pixels)/2))
                    r = int( ((pixels[pixel3]['r'])**2+(pixels[pixel4]['r'])**2) ** (1/2) ) # function to calulcate desired values
                    g = int( ((pixels[pixel3]['g'])**2+(pixels[pixel4]['g'])**2) ** (1/2) )
                    b = int( ((pixels[pixel3]['b'])**2+(pixels[pixel4]['b'])**2) ** (1/2) )
                    # r,g and b used later in the bulb transition/flow
                
                elif position == 'top-average':
                    pixels = layer1['top']
                    r_sum, g_sum, b_sum = 0,0,0
                    for pixel in pixels:
                        r_sum = r_sum + ((pixel['r']) ** 2)
                        g_sum = g_sum + ((pixel['g']) ** 2)
                        b_sum = b_sum + ((pixel['b']) ** 2)
                    r = int((r_sum/len(pixels))*(1/2))
                    g = int((g_sum/len(pixels))*(1/2))
                    b = int((b_sum/len(pixels))*(1/2))
                elif position == 'right-average':
                    pixels = layer1['right']
                    r_sum, g_sum, b_sum = 0,0,0
                    for i in range(0,len(pixels)):
                        pixel = str(int(i))
                        r_sum = r_sum + ((pixels[pixel]['r']) ** 2)
                        g_sum = g_sum + ((pixels[pixel]['g']) ** 2)
                        b_sum = b_sum + ((pixels[pixel]['b']) ** 2)
                    r = int((r_sum/len(pixels))**(1/2))
                    g = int((g_sum/len(pixels))**(1/2))
                    b = int((b_sum/len(pixels))**(1/2))
                elif position == 'left-average':
                    pixels = layer1['left']
                    r_sum, g_sum, b_sum = 0,0,0
                    for pixel in pixels:
                        r_sum = r_sum + ((pixel['r']) ** 2)
                        g_sum = g_sum + ((pixel['g']) ** 2)
                        b_sum = b_sum + ((pixel['b']) ** 2)
                    r = int((r_sum/len(pixels))*(1/2))
                    g = int((g_sum/len(pixels))*(1/2))
                    b = int((b_sum/len(pixels))*(1/2))
                elif position == 'bottom-average':
                    pixels = layer1['bottom']
                    r_sum, g_sum, b_sum = 0,0,0
                    for pixel in pixels:
                        r_sum = r_sum + ((pixel['r']) ** 2)
                        g_sum = g_sum + ((pixel['g']) ** 2)
                        b_sum = b_sum + ((pixel['b']) ** 2)
                    r = int((r_sum/len(pixels))*(1/2))
                    g = int((g_sum/len(pixels))*(1/2))
                    b = int((b_sum/len(pixels))*(1/2))
                elif position == 'top-middle' or position == 'top-center' or position == 'top':
                    pixels = layer1['top']
                    pixel = str(int(len(pixels)/2))
                    r = int(pixels[pixel]['r'])
                    g = int(pixels[pixel]['g'])
                    b = int(pixels[pixel]['b'])
                elif position == 'bottom-middle' or position == 'bottom-center' or position == 'bottom':
                    pixels = layer1['bottom']
                    pixel = str(int(len(pixels)/2))
                    r = int(pixels[pixel]['r'])
                    g = int(pixels[pixel]['g'])
                    b = int(pixels[pixel]['b'])
                elif position == 'right':
                    pixels = layer1['right']
                    pixel = str(int(len(pixels)/2))
                    r = int(pixels[pixel]['r'])
                    g = int(pixels[pixel]['g'])
                    b = int(pixels[pixel]['b'])
                elif position == 'left':
                    pixels = layer1['left']
                    pixel = str(int(len(pixels)/2))
                    r = int(pixels[pixel]['r'])
                    g = int(pixels[pixel]['g'])
                    b = int(pixels[pixel]['b'])
                elif position == 'top-right-average':
                    r_sum, g_sum, b_sum = 0,0,0
                    rightpixels = layer1['right']
                    rtpixel = rightpixels['0']
                    toppixels = layer1['top']
                    trpixel = toppixels[str(int(len(toppixels)-1))]
                    selected_pixels = [rtpixel,trpixel]
                    for pixel in selected_pixels:
                        r_sum = r_sum + ((pixel['r']) ** 2)
                        g_sum = g_sum + ((pixel['g']) ** 2)
                        b_sum = b_sum + ((pixel['b']) ** 2)
                    r = int((r_sum/len(selected_pixels))*(1/2))
                    g = int((g_sum/len(selected_pixels))*(1/2))
                    b = int((b_sum/len(selected_pixels))*(1/2))
                elif position == 'top-left-average':
                    r_sum, g_sum, b_sum = 0,0,0
                    leftpixels = layer1['left']
                    ltpixel = leftpixels[str(int(len(leftpixels)-1))]
                    toppixels = layer1['top']
                    tlpixel = toppixels['0']
                    selected_pixels = [ltpixel,tlpixel]
                    for pixel in selected_pixels:
                        r_sum = r_sum + ((pixel['r']) ** 2)
                        g_sum = g_sum + ((pixel['g']) ** 2)
                        b_sum = b_sum + ((pixel['b']) ** 2)
                    r = int((r_sum/len(selected_pixels))*(1/2))
                    g = int((g_sum/len(selected_pixels))*(1/2))
                    b = int((b_sum/len(selected_pixels))*(1/2))
                elif position == 'bottom-right-average':
                    r_sum, g_sum, b_sum = 0,0,0
                    rightpixels = layer1['right']
                    rbpixel = rightpixels[str(int(len(rightpixels)-1))]
                    bottompixels = layer1['bottom']
                    rbpixel = bottompixels[str(int(len(bottompixels)-1))]
                    selected_pixels = [rbpixel,brpixel]
                    for pixel in selected_pixels:
                        r_sum = r_sum + ((pixel['r']) ** 2)
                        g_sum = g_sum + ((pixel['g']) ** 2)
                        b_sum = b_sum + ((pixel['b']) ** 2)
                    r = int((r_sum/len(selected_pixels))*(1/2))
                    g = int((g_sum/len(selected_pixels))*(1/2))
                    b = int((b_sum/len(selected_pixels))*(1/2))
                elif position == 'bottom-left-average':
                    r_sum, g_sum, b_sum = 0,0,0
                    leftixels = layer1['left']
                    lbpixel = leftixels['0']
                    bottompixels = layer1['bottom']
                    blpixel = bottomixels['0']
                    selected_pixels = [lbpixel,blpixel]
                    for pixel in selected_pixels:
                        r_sum = r_sum + ((pixel['r']) ** 2)
                        g_sum = g_sum + ((pixel['g']) ** 2)
                        b_sum = b_sum + ((pixel['b']) ** 2)
                    r = int((r_sum/len(selected_pixels))*(1/2))
                    g = int((g_sum/len(selected_pixels))*(1/2))
                    b = int((b_sum/len(selected_pixels))*(1/2))
                elif position == 'right-top':
                    pixels = layer1['right']
                    r = int(pixels['0']['r'])
                    g = int(pixels['0']['g'])
                    b = int(pixels['0']['b'])
                elif position == 'left-top':
                    pixels = layer1['left']
                    pixel = str(int(len(pixels)-1))
                    r = int(pixels[pixel]['r'])
                    g = int(pixels[pixel]['g'])
                    b = int(pixels[pixel]['b'])
                elif position == 'top-left':
                    pixels = layer1['top']
                    r = int(pixels['0']['r'])
                    g = int(pixels['0']['g'])
                    b = int(pixels['0']['b'])
                elif position == 'top-right':
                    pixels = layer1['top']
                    pixel = str(int(len(pixels)-1))
                    r = int(pixels[pixel]['r'])
                    g = int(pixels[pixel]['g'])
                    b = int(pixels[pixel]['b'])
                elif position == 'right-bottom':
                    pixels = layer1['right']
                    pixel = str(int(len(pixels)-1))
                    r = int(pixels[pixel]['r'])
                    g = int(pixels[pixel]['g'])
                    b = int(pixels[pixel]['b'])
                elif position == 'left-bottom':
                    pixels = layer1['left']
                    r = int(pixels['0']['r'])
                    g = int(pixels['0']['g'])
                    b = int(pixels['0']['b'])
                elif position == 'bottom-left':
                    pixels = layer1['bottom']
                    r = int(pixels['0']['r'])
                    g = int(pixels['0']['g'])
                    b = int(pixels['0']['b'])
                elif position == 'bottom-right':
                    pixels = layer1['bottom']
                    pixel = str(int(len(pixels)-1))
                    r = int(pixels[pixel]['r'])
                    g = int(pixels[pixel]['g'])
                    b = int(pixels[pixel]['b'])

                if r == None and g == None and b == None: # incase of a failure somewhere
                    r,g,b = DEFAULT_RGB_COLOR[0], DEFAULT_RGB_COLOR[1], DEFAULT_RGB_COLOR[2]
                    self._bulb.set_brightness(0)
                if r == 0 and g == 0 and b == 0: # dim bulb in game mode
                    if ambiSetting['menuSetting'] == "GAME":
                        r,g,b = DEFAULT_RGB_COLOR[0], DEFAULT_RGB_COLOR[1], DEFAULT_RGB_COLOR[2]
                        self._bulb.set_brightness(0)
                else:
                    if ambiSetting['styleName'] == "FOLLOW_VIDEO":
                        transitions = [RGBTransition(r,g,b,duration=400)] # this transition can be customised (see: https://yeelight.readthedocs.io/en/latest/yeelight.html#yeelight.Flow)
                    else:
                        transitions = [RGBTransition(r,g,b,duration=200)]
                    flow = Flow(
                        count=1,
                        action=Flow.actions.stay,
                        transitions=transitions)
                    self._bulb.start_flow(flow)
                time.sleep(sleep)
            except:
                print('Failed to transfer color values')
                self.turn_off()
                
    def _getReq(self, path):
        try:
            if self._connfail:
                self._connfail -= 1
                return None
            resp = self._session.get(BASE_URL.format(self._tvip, path), verify=False, auth=HTTPDigestAuth(self._user, self._password), timeout=TIMEOUT)
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
            resp = self._session.post(BASE_URL.format(self._tvip, path), data=json.dumps(data), verify=False, auth=HTTPDigestAuth(self._user, self._password), timeout=TIMEOUT)
            self.on = True
            return json.loads(resp.text)
        except requests.exceptions.RequestException as err:
            self._connfail = CONNFAILCOUNT
            self.on = False
            return False