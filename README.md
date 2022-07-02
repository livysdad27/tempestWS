    tempestWS readme.md Copyright (C) 2022 - Billy Jackson

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.

# tempestWS Weewx Driver
This is a [weewx](https://weewx.com) driver for the [Weatherflow Tempest](https://weatherflow.com/tempest-weather-system/) device.  This version makes use of the [Websocket](https://weatherflow.github.io/Tempest/api/ws.html) API.

The primary use case for this driver is running a weewx server in the cloud so that I don't have to rely on a local device to forward reports to a web server.  One fairly inexpensive cloud server can handle both tasks.  I choose the websocket API because it submits more data than querying the REST API, with some exceptions.  They have a pretty good [geting started guide](https://weatherflow.github.io/Tempest/api/) that covers a lot of the basics.

They also offer a local broadcast [UDP API](https://weatherflow.github.io/Tempest/api/udp/v171/).  This is especially useful for use cases where you might be off-grid and want to capture to a local server.  It also works well with a Raspberry Pi if you like to mess around with that sort of thing.  There are some differences in data available.  For example, I can get the RSSI/signal strength fields this way but not through the websocket or rest API.  If you're intersted in running in this mode I highly recommend the [weatherflow-udp](https://github.com/captain-coredump/weatherflow-udp) driver by captain-coredump.  I've run this setup for several months and it works really well.

To install and use this driver you will need to have a personal access token (see the [geting started guide](https://weatherflow.github.io/Tempest/api/)), and your device ID.  Note that your device ID is different than the ST number or the station ID. You may see in your device's website or mobile application.  You can find this under the settings -> stations -> your station name -> status options in your app.  Alternately once you're familiar witht the API you can get a token, authorize the [Tempest API Explorer](https://weatherflow.github.io/Tempest/api/swagger/#!/stations/getStations) and find the device ID in the output of the /stations endpoint. 

## Installation Prerequisites
This implementation requires the [python websocket-client library](https://pypi.org/project/websocket-client/) to work.  Prior to installing the driver it should be installed.  The command below will work on many systems.

`pip3 install websocket-client`

In addition this driver has ONLY been tested with python3 and will likely have issues if you attempt to run it on an older implementation.  It's been tested on weewx 4.8.0.

## Installation Steps
The [wee_extension](https://www.weewx.com/docs/utilities.htm#wee_extension_utility) utility is the best way to do the installation followed by a [wee_config](https://weewx.com/docs/utilities.htm#wee_config_utility).  You can run it against either a zip, gz or directory that has been cloned from the github repo.  I find it easiest, since I'm running on a cloud server, to use git to clone the repo.  This has the added benefits of letting you edit and reinstall locally if you'd like.

`git clone https://github.com/livysdad27/tempestWS
wee_extension --install tempestWS
wee_config --reconfigure --driver=user.tempestWS --no-prompt`

After these steps the driver will be set as the default driver and the configuration options will appear in your weewx.conf.  Upon restarting however weewx will crash because there isn't yet a personal token or device ID in the file.  Now you'll want to open your weewx.conf and edit the stanza below.

`[tempestWS]
    driver = user.tempestWS
    personal_token = your_api_token
    tempest_device_id = your_tempest_device_id
    tempest_ws_endpoint = wss://ws.weatherflow.com/swd/data
    rest_sleep_interval = 20`

* Replace the `your_api_token` with your personal token that you configured in your Tempest web application as referenced in the [geting started guide](https://weatherflow.github.io/Tempest/api/).
* Replace the `your_tempest_device_id` with the device id that you found in the [Tempest API Explorer](https://weatherflow.github.io/Tempest/api/swagger/#!/stations/getStations) or in your web application (settings -> stations -> your station name -> status options).

Restart weewx and you should be on your way!

### Todos
I welcome pull requests or recommendations.  I ask that if you submit a pull request you include at least what versions of python and weewx you've tested on along with the operating system so that we can track what works where.  

* Think through branching and clearer guidelines for pull requests.  
* Continue exploring if the wee_extension can reord the config stanza like it does with skins.
* Add connection failure code and retry count in case the websocket API goes down so that weewx doesn't crash it comes back up.

