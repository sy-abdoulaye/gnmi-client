from pygnmi.client import gNMIclient as GnmiClient, telemetryParser
from helper import GetLogger, parse_args, load_data
from concurrent.futures import ThreadPoolExecutor, as_completed
from json import dumps as json_dumps
from os import makedirs as os_mdirs
from os.path import join as os_path_join
from yaml import dump as yaml_dump

LOGGER = GetLogger.setup_logging()

class Subscribe():
    """
    Basic gNMI client that is able to subscribe sensors. 

    How to run:
        python gnmi_c/subscribe.py --testbed testbed.yaml --devices lille-core-ncs5k8-1 
    """
    def collect_gnmi_data(self, device_name):
        """
        Connects to a specified device using gNMI and retrieves its capabilities.

        This method extracts connection details and credentials from the loaded testbed
        configuration, connects to the gNMI service on the device, and retrieves its
        capabilities. Results are returned in dictionary format and also logged.

        Args:
            device_info (str): The name or identifier of the device to connect to.

        Returns:
            dict: A dictionary containing the device host as the key and either
                the retrieved capabilities or an error message as the value.
        """
        # extracts connection details and credentials from the loaded testbed
        gnmi_data = self.testbed.get('devices').get(device_name).get('connections').get('gnmi')
        host = gnmi_data.get('host')
        port = gnmi_data.get('port', 57400)

        login_creds = gnmi_data.get('login_creds')
        login_data = self.testbed.get('testbed').get('credentials').get(login_creds)
        username = login_data.get('username')
        password = login_data.get('password')

        LOGGER.info(f"Connecting to {host}")

        subscribe_request = {

            'subscription':[
                {
                    'path':'openconfig-interfaces:interfaces/interface[name=MgmtEth0/RP0/CPU0/0]',
                    'mode':'sample',
                    'sample_interval':10000000000
                },
                # {
                #     'path':'Cisco-IOS-XR-rsi-agent-oper:rsi-agent/nodes/',
                #     'mode':'sample',
                #     'sample_interval':10000000000
                # }
            ],
            'mode':'stream',
            'encoding':'proto'

        }
        try:
            target = (host, port)
            with GnmiClient(target=target, username=username, password=password, insecure=True) as gnmi_context:
                telemetry_stream = gnmi_context.subscribe(subscribe=subscribe_request)

                # Dumped the capabilities data to yaml file for more readable
                output_dir = f"gnmi_outputs/{device_name}"
                os_mdirs(output_dir, exist_ok=True)
                output_file = os_path_join(output_dir, "subscribe.yaml")
                
                for data in telemetry_stream:
                    with open(output_file, "w") as f:
                        yaml_dump({host: telemetryParser(data)}, f, default_flow_style=False)
                    print(json_dumps((telemetryParser(data)), indent=4))
                # return {host: capabilities}
        except Exception as e:
            LOGGER.error(f"Error connecting to {host}: {e}")
            return {host: str(e)}
    
    def parsr_args_run_task(self):
        """
        This method parses command-line arguments, loads the testbed configuration,
        and concurrently collects gNMI data from specified devices.
        """
        kwargs = parse_args(return_kwargs=True)
        devices = kwargs.get('devices')
        testbed_file = kwargs.get('testbed')

        self.testbed = load_data(
            file_extension='yaml',
            file_path=f"gnmi_c/{testbed_file}"
        )

        if devices:
            devices = devices.split(' ')

        results = []
        with ThreadPoolExecutor(max_workers=len(devices)) as executor:
            futures = [executor.submit(self.collect_gnmi_data, device) for device in devices]
            for future in as_completed(futures):
                results.append(future.result())
        LOGGER.info(f"gNMI Results:\n{json_dumps(results, indent=2)}")

if __name__ == '__main__':
    Subscribe().parsr_args_run_task()