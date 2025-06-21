from pygnmi.client import gNMIclient as GnmiClient
from utils.helper import GetLogger
from os import makedirs as os_mdirs
from os.path import join as os_path_join
from yaml import dump as yaml_dump

LOGGER = GetLogger.setup_logging()

class Capabilities():
    """
    Basic gNMI client that is able to query the capabilities of a network device. 
    """
    def collect_gnmi_data(self, testbed, device_name):
        """
        Connects to a network device using gNMI and retrieves its capabilities.

        This method extracts connection parameters and credentials from the provided
        testbed data structure, then initiates a gNMI client session to the specified
        device. It fetches and logs the gNMI capabilities, and writes the output to
        a YAML file in a device-specific directory.

        Args:
            testbed (dict): A dictionary representing the testbed configuration,
                            containing device connection details and credentials.
            device_name (str): The name of the device to connect to within the testbed.

        Returns:
            dict: A dictionary containing the device host as the key and either the
                retrieved capabilities or an error message as the value.
        """
        # extracts connection details and credentials from the loaded testbed
        gnmi_data = testbed.get('devices').get(device_name).get('connections').get('gnmi')
        host = gnmi_data.get('host')
        port = gnmi_data.get('port', 57400)

        login_creds = gnmi_data.get('login_creds')
        login_data = testbed.get('testbed').get('credentials').get(login_creds)
        username = login_data.get('username')
        password = login_data.get('password')

        LOGGER.info(f"Connecting to {host}")
        try:
            target = (host, port)
            with GnmiClient(target=target, username=username, password=password, insecure=True) as gnmi_context:
                capabilities = gnmi_context.capabilities()

                # Dumped the capabilities data to yaml file for more readable
                output_dir = f"gnmi_outputs/{device_name}"
                os_mdirs(output_dir, exist_ok=True)
                output_file = os_path_join(output_dir, "capabilities.yaml")
                with open(output_file, "w") as f:
                    yaml_dump({host: capabilities}, f, default_flow_style=False)

                return {host: capabilities}
        except Exception as e:
            LOGGER.error(f"Error connecting to {host}: {e}")
            return {host: str(e)}