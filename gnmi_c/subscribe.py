from pygnmi.client import gNMIclient as GnmiClient, telemetryParser
from utils.helper import GetLogger, parse_args, load_data
from concurrent.futures import ThreadPoolExecutor, as_completed
from json import dumps as json_dumps
from os import makedirs as os_mdirs
from os.path import join as os_path_join
from yaml import dump as yaml_dump

LOGGER = GetLogger.setup_logging()

class Subscribe():
    """
    Basic gNMI client that is able to subscribe sensors. 
    """
    def collect_gnmi_data(self, testbed, device_name):
        """
        Connects to a specified device using gNMI and retrieves its capabilities.

        This method extracts connection details and credentials from the loaded testbed
        configuration, connects to the gNMI service on the device, and retrieves its
        capabilities. Results are returned in dictionary format and also logged.

        Args:
            testbed (dict): A dictionary representing the testbed configuration,
                            containing device connection details and credentials.
            device_name (str): The name of the device to connect to within the testbed.
        Returns:
            dict: A dictionary containing the device host as the key and either
                the retrieved capabilities or an error message as the value.
        """
        # extracts connection details and credentials from the loaded testbed
        gnmi_data = testbed.get('devices').get(device_name).get('connections').get('gnmi')
        host = gnmi_data.get('host')
        port = gnmi_data.get('port', 57400)
        device_subscriptions = gnmi_data.get('subscriptions')

        login_creds = gnmi_data.get('login_creds')
        login_data = testbed.get('testbed').get('credentials').get(login_creds)
        username = login_data.get('username')
        password = login_data.get('password')

        subscrptions_request = {
            'subscription':[],
            'mode': 'stream',
            'encoding': 'json'
        }

        LOGGER.info(f"Connecting to {host}")
        for subscription in device_subscriptions:
            sensors_path = testbed.get('subscriptions').get(subscription)
            subscrptions_request.get('subscription').append(sensors_path)
        
        try:
            target = (host, port)
            with GnmiClient(target=target, username=username, password=password, insecure=True, no_qos_marking=True) as gnmi_context:
                telemetry_stream = gnmi_context.subscribe(subscribe=subscrptions_request)

                # Dumped the capabilities data to yaml file for more readable
                output_dir = f"gnmi_outputs/{device_name}"
                os_mdirs(output_dir, exist_ok=True)
                output_file = os_path_join(output_dir, "subscribe.yaml")
                
                for data in telemetry_stream:
                    with open(output_file, "w") as f:
                        yaml_dump({host: telemetryParser(data)}, f, default_flow_style=False)
                    print(json_dumps((telemetryParser(data)), indent=4))
        except Exception as e:
            LOGGER.error(f"Error connecting to {host}: {e}")
            return {host: str(e)}