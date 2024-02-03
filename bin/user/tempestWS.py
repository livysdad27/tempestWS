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

import socket
from websocket import create_connection
from websocket._exceptions import WebSocketConnectionClosedException
from websocket._exceptions import WebSocketTimeoutException
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
        syslog.syslog(level, 'tempestWS: %s:' % msg)

    def logdbg(msg):
        logmsg(syslog.LOG_DEBUG, msg)

    def loginf(msg):
        logmsg(syslog.LOG_INFO, msg)

    def logerr(msg):
        logmsg(syslog.LOG_ERR, msg)
    
    loginf("Using old-style logging.")

class TooManyRetries(Exception):
    pass

# Helper function to see if our start commands return good data.  
def check_cmd_response(cmd_resp):
    if cmd_resp == "":
        logerr("Null response from the websocket, is something awry?")
    try:
        resp = json.loads(cmd_resp)
    except json.decoder.JSONDecodeError:
        logerr("Caught a decode error during a checkResponse")

    if "type" in resp:
        if resp["type"] == 'connection_opened':
            loginf("Successfully received open connection response!")
        elif resp["type"] == 'ack':
            loginf ("Received a positive ack response for " + str(resp["id"]))
    elif "status" in resp:
        if resp["status"]["status_message"] == "SUCCESS":
            loginf("SUCCESS response from listen_start_events message.")
    else:
        logerr("I don't recognize this at all: " + str(resp))
    

# Helper function to send restart commands during connect/reconnect.  This will let me move the
# check/validation code for a connection and start commands here as a todo
def send_listen_start_cmds(sock, dev_id, stn_id):
    sock.send('{"type":"listen_rapid_start",' + ' "device_id":' + dev_id + ',' + ' "id":"listen_rapid_start"}')
    check_cmd_response(sock.recv())
    sock.send('{"type":"listen_start",' + ' "device_id":' + dev_id + ',' + ' "id":"listen_start"}')
    check_cmd_response(sock.recv())
    sock.send('{"type":"listen_start_events",' + ' "device_id":' + stn_id + ',' + ' "id":"listen_start_events"}')
    check_cmd_response(sock.recv())


DRIVER_VERSION = "1.0.1"
HARDWARE_NAME = "Weatherflow Tempest Websocket"
DRIVER_NAME = "tempestWS"

# Spit out the version info for troubleshooting purposes.  Need to remember to bunp versions.
loginf("Loading " + DRIVER_NAME + " " + HARDWARE_NAME + " " + DRIVER_VERSION)

def loader(config_dict, engine):
    return tempestWS(**config_dict[DRIVER_NAME])

# Inherit and initiate the class.  The sleep interval param isn't used currently but I left
# it in just in case it's useful to pull that data also.
class tempestWS(weewx.drivers.AbstractDevice):
    def __init__(self, **cfg_dict):
        self._personal_token = str(cfg_dict.get('personal_token'))
        self._tempest_device_id = str(cfg_dict.get('tempest_device_id'))
        self._tempest_station_id = str(cfg_dict.get('tempest_station_id'))
        self._tempest_ws_endpoint = str(cfg_dict.get('tempest_ws_endpoint'))
        self._reconnect_sleep_interval = int(cfg_dict.get('reconnect_sleep_interval'))
        self._ws_uri=self._tempest_ws_endpoint + '?token=' + self._personal_token

        # Connect to the websocket and issue the starting commands for rapid and listen packets.
        loginf("Starting the websocket connection to " + self._tempest_ws_endpoint)
        self.ws = create_connection(self._ws_uri)
        check_cmd_response(self.ws.recv())
        send_listen_start_cmds(self.ws, self._tempest_device_id, self._tempest_station_id)

    def hardware_name(self):
        return HARDWARE_NAME

    def closePort(self):
        # Shut down the events if the driver is closed.
        loginf("Stopping messages and closing websocket")
        self.ws.send('{"type":"listen_rapid_stop",' + ' "device_id":' + self._tempest_device_id + ',' + ' "id":"listen_rapid_stop"}')
        resp_listen_rapid_stop = self.ws.recv()
        loginf("Listen_rapid_stop response:" + str(resp_listen_rapid_stop))
        self.ws.send('{"type":"listen_stop",' + ' "device_id":' + self._tempest_device_id + ',' + ' "id":"listen_stop"}')
        resp_listen_stop = self.ws.recv()
        loginf("Listen_stop response:" + str(resp_listen_stop))
        self.ws.send('{"type":"listen_stop_events",' + ' "station_id":' + self._tempest_station_id + ',' + ' "id":"listen_stop_events"}')
        resp_listen_events_stop = self.ws.recv()
        loginf("Listen_stop_events response:" + str(resp_listen_events_stop))
        self.ws.close()
        
    # This is where the loop packets are made via a call to the rest API endpoint
    def genLoopPackets(self):
        retries = 0
        while True:
            loop_packet = {}
            mqtt_data = []

            # First, check to see if the connection died and retry if it did
            try:
                raw_resp = self.ws.recv()
                if raw_resp == "":
                    logerr("Caught a null response in the genLoopPackets loop.")
            except (WebSocketConnectionClosedException, WebSocketTimeoutException) as e:
                logerr("Caught a " + str(type(e)) + ", attempting to reconnect!  Try " +str(retries))
                time.sleep(self._reconnect_sleep_interval)
                self.ws.connect(self._ws_uri)
                check_cmd_response(self.ws.recv())
                send_listen_start_cmds(self.ws, self._tempest_device_id, self._tempest_station_id)
                retries += 1
                continue

            # Grab the response and check that it's good JSON.
            try:
                resp = json.loads(raw_resp)
            except json.decoder.JSONDecodeError:
                logerr("Caught a decode error, restarting loop, data follows: " + str(raw_resp))
                continue
            if "type" in resp:
                if resp['type'] == 'obs_st':
                    mqtt_data = resp['obs'][0]
                    loop_packet['dateTime'] = mqtt_data[0]
                    loop_packet['usUnits'] = weewx.METRICWX
                    loop_packet['outTemp'] = mqtt_data[7]
                    loop_packet['outHumidity'] = mqtt_data[8]
                    loop_packet['pressure'] = mqtt_data[6]
                    loop_packet['supplyVoltage'] = mqtt_data[16]
                    loop_packet['radiation'] = mqtt_data[11]
                    loop_packet['rain'] = mqtt_data[12]
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
                #The evt_precip and evt_strike code below is a test.
                elif resp['type'] == 'evt_strike':
                    loginf("It started lightning.  evt_strike received" + str(resp))
                    mqtt_data = resp['evt']
                    loop_packet['dateTime'] = mqtt_data[0]
                    loop_packet['lightning_strike_count'] = 1
                    loop_packet['usUnits'] = weewx.METRICWX
                    loop_packet['lightning_distance'] = mqtt_data[1]
                elif resp['type'] == 'evt_precip':
                    loginf("It started raining.  evt_precip received" + str(resp))
                elif resp['type'] == 'evt_station_offline':
                    loginf("Station offline event detected" +str(resp))
                elif resp['type'] == 'evt_station_online':
                    loginf("Station online event detected" +str(resp))
                elif resp['type'] == 'evt_device_offline':
                    loginf("Device offline event detected" +str(resp))
                elif resp['type'] == 'evt_device_online':
                    loginf("Device online event detected" +str(resp))
            else: 
                loginf("Unknown message has no type: " + str(resp))
            
            if loop_packet != {}:
                yield loop_packet

# To test this driver, run it directly as follows:
#   PYTHONPATH=/home/weewx/bin python /home/weewx/bin/user/tempestWS.py
if __name__ == "__main__":
    import weewx
    import weeutil.weeutil
    try:
      import weeutil.logger

      weewx.debug = 1
      weeutil.logger.setup('tempestWS', {})
    except:
      pass

    driver = tempestWS()
    for packet in driver.genLoopPackets():
        print(weeutil.weeutil.timestamp_to_string(packet['dateTime']), packet)
