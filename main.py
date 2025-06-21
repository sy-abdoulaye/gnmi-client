"""

How to run gnmi client:
    python main.py --testbed testbed.yaml --devices lille-core-ncs5k8-1 --action <capabilities|subscribe>

    Example:
    python main.py --testbed testbed.yaml --devices lille-core-ncs5k8-1 lille-core-mx10k8-1 --action capabilities
    python main.py --testbed testbed.yaml --devices lille-core-ncs5k8-1 --action subscribe
    python main.py --testbed testbed.yaml --devices lille-core-mx10k8-1 --action subscribe
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils.helper import load_data, parse_args
from utils.helper import GetLogger
from gnmi_c.capabilities import Capabilities
from gnmi_c.subscribe import Subscribe
from json import dumps as json_dumps

LOGGER = GetLogger.setup_logging()

def run_gnmi_task(task_class, testbed, device_names=None):
    """
    Orchestrates the gNMI task (capabilities or subscribe) concurrently.

    Args:
        task_class (Capabilities or Subscribe): The task class instance to run.
        testbed_file (str): Path to the testbed YAML file.
        device_names (list[str], optional): List of device names to target. If None, all devices are used.
    """
    task = task_class()
    
    results = []
    with ThreadPoolExecutor(max_workers=len(device_names)) as executor:
        futures = [executor.submit(task.collect_gnmi_data, testbed, device_name) for device_name in device_names]
        for future in as_completed(futures):
            results.append(future.result())

    LOGGER.info(f"gNMI Results:\n{json_dumps(results, indent=2)}")
    
def main():
    kwargs = parse_args(return_kwargs=True)
    devices = kwargs.get('devices')
    testbed_file = kwargs.get('testbed')
    action = kwargs.get('action')

    try:
        testbed = load_data(
            file_extension='yaml',
            file_path=f"gnmi_c/{testbed_file}"
        )
    except Exception as e:
        LOGGER.error("Error when loading the testbed file")
        return

    device_list = devices.split() if devices else list(testbed.get('devices').keys())
    
    if action == 'capabilities':
        LOGGER.info("Running gNMI Capabilities colection...")
        run_gnmi_task(Capabilities, testbed, device_list)
    elif action == 'subscribe':
        LOGGER.info("Running gNMI Subscription stream...")
        run_gnmi_task(Subscribe, testbed, device_list)
    else:
        LOGGER.error("Invalid action provided...")
        return
    
if __name__=='__main__':
    main()