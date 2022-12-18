> ### Update:
>
> To support [HACS](https://community.home-assistant.io/t/custom-component-hacs/121727), this repository has been broken up into three
> - The Philips TV Ambilight (Light) Component (philips_ambilight)
> - The [Ambilight+Hue ON/OFF (Switch)](https://github.com/jomwells/ambihue) Component (philips_ambilight+hue)
> - The (new) [Ambilight+Yeelight (Switch)](https://github.com/jomwells/ambilight-yeelight) Component (philips_ambilight+yeelight)



# Philips TV Ambilight (Light) Component for Home Assistant

This custom component utilizes the [JointSpace API](http://jointspace.sourceforge.net/projectdata/documentation/jasonApi/1/doc/API.html) to control the Ambilight on a 2016+ Philips Android TV from within Home Assistant

> ### New in this Version:
> - All components updated for the 'Great Migration' (thanks [hutchinsane](https://github.com/hutchinsane))
> - There is apparently an issue for setting the ambilight brightness on some TV's where the colour is always changed, even when in manual mode, I have implemented a potential workaround for this using a method highlighted by [gyrga](https://community.home-assistant.io/u/gyrga), but it is commented out by default. See Line 130 in ```light.py```

### For more help with this component, see the [discussion](https://community.home-assistant.io/t/philips-android-tv-ambilights-light-component/67754) on community.home-assistant.io

## Installation

If you have not already done so for another component, first Pair with your TV to generate the username and password using [this tool](https://github.com/suborb/philips_android_tv) and save the username and password in ```secrets.yaml```

#### Option 1: (recommended)
This repository is compatible with the Home Assistant Community Store ([HACS](https://community.home-assistant.io/t/custom-component-hacs/121727)).

After installing HACS, install 'Ambilights' from the store, and use the ```configuration.yaml``` example below.

#### Option 2: (manual)
Download this repository as a zip file, and place the ```philips_ambilight``` directory in your ```config/custom_components/``` directory.

Configure according to the following example and restart Home Assistant.

```
light:
  - platform: philips_ambilight
    name: Bedroom Ambilight
    host: 192.168.1.XXX
    username: !secret philips_username
    password: !secret philips_password
```

## Features
This component has the following features:
- Power Ambilight ON/OFF
- Brightness
- RGB colour
- Transition
  - Support for smooth transition between color and brightness.
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
  
Individual effects can be easily removed from the Front-End by removing them from the ```AMBILIGHT_EFFECT_LIST``` (line 53 of ```light.py``` in the ```philips_ambilight``` folder.)

## Known Issues
- The light component can turn the Ambilight on when the TV is off, however, after the TV has been in standby for a long period of time, the component will lose connection, and will be unable to turn the lights on again until the TV is woken up and reconnects - this can be solved by manually turning on the TV and then changing the ambilight, or through the use of an IR blaster connected to Home Assistant to achieve the same result. Alternatively you can install the Wakelock app (https://github.com/d4rken/wakelock-revamp/releases/latest) and enable `Processor` and `Screen dimmed` wakelocks (and enable the app at startup) so that the TV remains online even when in sleep mode.

## Older Philips TV's
Older (non-Android) Philips TV's with ambilight, which use the JointSpace API, may be controllable through this component, try changing the `BASE_URL` on line 20 to `http://{0}:1925/1/{1}`. Note: as the older API does not use HTTPS, there is no need for the `username` and  `password` fields to be generated or placed into your `configuration.yaml`, there may also be changes needed to the `_getReq()` and `_postReq()` sections to accommodate this, If anyone is successful with this, let me know and I will update this section.
