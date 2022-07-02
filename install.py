from setup import ExtensionInstaller

def loader():
    return tempestWSInstaller()

class tempestWSInstaller(ExtensionInstaller):
    def __init__(self):
        super(tempestWSInstaller, self).__init__(
            version=".7",
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
                    'tempest_ws_endpoint': 'wss://ws.weatherflow.com/swd/data',                        
                    'rest_sleep_interval': '20'
                },
            }
        )