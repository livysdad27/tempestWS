"""
This is a weewx driver for the Weatherflow Tempest system that works via it's websocket API
Copyright (C) 2022 - Billy Jackson

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
"""

from websocket import create_connection
import time
import json
import weewx.drivers
import weewx.units
import weewx.wxformulas
import weedb
import weeutil.weeutil
import syslog
import getopt

try:
    # Test for new-style weewx logging by trying to import weeutil.logger
    import weeutil.logger
    import logging
    log = logging.getLogger(__name__)

    def logdbg(msg):
        log.debug(msg)

    def loginf(msg):
        log.info(msg)

    def logerr(msg):
        log.error(msg)
    
    loginf("Using new-style logging!")

except ImportError:
    # Old-style weewx logging
    import syslog

    def logmsg(level, msg):
        syslog.syslog(level, 'tempestAPI: %s:' % msg)

    def logdbg(msg):
        logmsg(syslog.LOG_DEBUG, msg)

    def loginf(msg):
        logmsg(syslog.LOG_INFO, msg)

    def logerr(msg):
        logmsg(syslog.LOG_ERR, msg)
    
    loginf("Using old-style logging.")


DRIVER_VERSION = "0.8"
HARDWARE_NAME = "Weatherflow Tempest Websocket"
DRIVER_NAME = "tempestWS"

def loader(config_dict, engine):
    return tempestWS(**config_dict[DRIVER_NAME])

# Inherit and initiate the class.  The station_id param isn't used currently but I left
# it in just in case it's useful to pull that data also.
class tempestWS(weewx.drivers.AbstractDevice):
    def __init__(self, **cfg_dict):
        self._personal_token = str(cfg_dict.get('personal_token'))
        self._tempest_device_id = str(cfg_dict.get('tempest_device_id'))
        self._tempest_station_id = str(cfg_dict.get('tempest_station_id'))
        self._tempest_ws_endpoint = str(cfg_dict.get('tempest_ws_endpoint'))
        self._rest_sleep_interval = int(cfg_dict.get('rest_sleep_interval'))
        self._ws_uri=self._tempest_ws_endpoint + '?api_key=' + self._personal_token

        # Connect to the websocket URI/endpoint prior to starting the main loop.
        self.ws = create_connection(self._ws_uri)
        resp = self.ws.recv()
        loginf(resp)

    def hardware_name(self):
        return HARDWARE_NAME

    def closePort(self):
        # Shut down the events if the driver is closed.
        self.ws.send('{"type":"listen_rapid_stop",' + ' "device_id":' + self._tempest_device_id + ',' + ' "id":"listen_rapid_stop"}')
        resp = self.ws.recv()
        loginf(resp)

        self.ws.send('{"type":"listen_stop",' + ' "device_id":' + self._tempest_device_id + ',' + ' "id":"listen_stop"}')
        resp = self.ws.recv()
        loginf(resp)

    # This is where the loop packets are made via a call to the rest API endpoint
    def genLoopPackets(self):
        loginf("Starting the websocket connection to " + self._tempest_ws_endpoint)

        # Fire up the listen_start and listen_rapid_start message types.  Rapid wind
        # provides the frequent wind direction/speed updates.  Listen_start gives you the 
        # summary and most importantly for this driver, the mqtt_data in the obs list.
        self.ws.send('{"type":"listen_rapid_start",' + ' "device_id":' + self._tempest_device_id + ',' + ' "id":"listen_rapid_start"}')
        self.ws.send('{"type":"listen_start",' + ' "device_id":' + self._tempest_device_id + ',' + ' "id":"listen_start"}')

        while True:
            loop_packet = {}
            mqtt_data = []
            try:
                resp = json.loads(self.ws.recv())
            except ValueError:
                logerr("Bad message received " + str(resp))

            if resp['type'] == 'obs_st':
                mqtt_data = resp['obs'][0]
                loop_packet['dateTime'] = mqtt_data[0]
                loop_packet['usUnits'] = weewx.METRICWX
                loop_packet['outTemp'] = mqtt_data[7]
                loop_packet['outHumidity'] = mqtt_data[8]
                loop_packet['pressure'] = mqtt_data[6]
                loop_packet['supplyVoltage'] = mqtt_data[16]
                loop_packet['radiation'] = mqtt_data[11]
                loop_packet['rain'] = mqtt_data[19]
                loop_packet['UV'] = mqtt_data[10]
                loop_packet['lightening_distance'] = mqtt_data[14]
                loop_packet['lightening_strike_count'] = mqtt_data[15]
                loop_packet['windDir'] = mqtt_data[4]
                loop_packet['windGust'] = mqtt_data[3]
                loop_packet['windSpeed'] = mqtt_data[1]
            elif resp['type'] == 'rapid_wind':
                mqtt_data = resp['ob']
                loop_packet['dateTime'] = mqtt_data[0]
                loop_packet['usUnits'] = weewx.METRICWX
                loop_packet['windSpeed'] = mqtt_data[1]
                loop_packet['windDir'] = mqtt_data[2]
            elif resp['type'] == 'ack':
                loginf("Ack received for command:" + str(resp))
            else: 
                loginf("Unknown packet type:" + str(resp))
            
            if loop_packet != {}:
                yield loop_packet