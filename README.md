# Philips Ambilight Light Component for Home Assistant
### and Ambilight+hue Switch Component (see below)

This custom component utilizes the [JointSpace API](http://jointspace.sourceforge.net/projectdata/documentation/jasonApi/1/doc/API.html) to control the Ambilight on a 2016+ Philips Android TV from within Home Assistant

### For more help with this component, see the [discussion](https://community.home-assistant.io/t/philips-android-tv-ambilights-light-component/67754) on community.home-assistant.io

## Installation
First Pair your TV, and generate the username and password using [this tool](https://github.com/suborb/philips_android_tv) and enter the details, along with the IP address of your TV into your configuration.yaml as follows:
```
light:
  - platform: philips_ambilight
    name: Bedroom Ambilight
    host: 192.168.1.XXX
    username: !secret philips_username
    password: !secret philips_password
```

**Place the 'light.py' in your 'config/custom_components/philips_ambilight/' directory, and restart Home Assistant**

## Features
This component has the following features:
- Power Ambilight ON/OFF
- Brightness
- RGB color
- Effects
  - Manual (custom RGB color for all LED's)
  - Standard (Follow Video)
  - Natural (Follow Video)
  - Football / Immersive (Follow Video)
  - Vivid (Follow Video)
  - Game (Follow Video)
  - Comfort (Follow Video)
  - Relax (Follow Video)
  - Lumina / Adaptive Brightness (Follow Audio)
  - Colora / Adaptive Color (Follow Audio)
  - Retro (Follow Audio)
  - Spectrum (Follow Audio)
  - Scanner (Follow Audio)
  - Rhythm (Follow Audio)
  - Party / Random (Follow Audio)
  
Individual effects can be easily removed from the Front-End by removing them from the 'AMBILIGHT_EFFECT_LIST' (line 53 of 'light.py' in the 'phlips_ambilight' folder.)

## Known Issues
- The light component can turn the Ambilight on when the TV is off, however, after the TV has been in standby for a long period of time, the component will loose connection, and will be unable to turn the lights on again until the TV is woken up and reconnects - this can be solved by manually turning on the TV and then changing the ambilight, or through the use of an IR blaster connected to Home Assistant to achieve the same result.

## Older Philips TV's
Older (non-Android) Philips TV's with ambilight, which use the JointSpace API, may be controllable through this component, try changing the `BASE_URL` on line 20 to `http://{0}:1925/1/{1}`. Note: as the older API does not use HTTPS, there is no need for the `username` and  `password` fields to be generated or placed into your `configuration.yaml`, there may also be changes needed to the `_getReq()` and `_postReq()` sections to accomodate this, If anyone is successful with this, let me know and I will update this section.

# Ambilight+hue Switch Component
For automating the control of the Ambilight+hue setting, use the additional Ambihue (Switch) component, this enables the status of the setting to be determined by Home Assistant, and allows for remote or automated toggling.
## Installation
If you have already setup the Ambilight component, the install of the switch component is very simple, place the 'switch.py' in your 'config/custom_components/philips_ambihue/' directory,
enter the same details as for the abilight component in the configuration.yaml as follows:
```
switch:
  - platform: philips_ambihue
    name: Ambilight+hue
    host: 192.168.1.XXX
    username: !secret philips_username
    password: !secret philips_password
    scan_interval: 5
```
*note* there is often a noticeable lag between Home Assistant sending the request to toggle the setting, and reciveing a status update from the API, for this reason, it is advised that you reduce your `scan_interval` (in seconds) to suit your needs.
