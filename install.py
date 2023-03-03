"""
This is the install.py for the Weatherflow Tempest driver that works via it's websocket API
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

from setup import ExtensionInstaller

def loader():
    return tempestWSInstaller()

class tempestWSInstaller(ExtensionInstaller):
    def __init__(self):
        super(tempestWSInstaller, self).__init__(
            version="1.0.1",
            name='tempestWS',
            description='Weatherflow Tempest Websocket Driver installer',
            author="Billy Jackson",
            author_email="livysdad27@gmail.com",
            files=[('bin/user', ['bin/user/tempestWS.py'])],
            config={
                'tempestWS': {
                    'driver' : 'bin.user.tempestWS',
                    'personal_token': 'your_api_token',
                    'tempest_device_id': 'your_tempest_device_id',
                    'tempest_station_id': 'your_tempest_station_id',
                    'tempest_ws_endpoint': 'wss://ws.weatherflow.com/swd/data',                        
                    'reconnect_sleep_interval': '20'
                },
            }
        )
