# gNMI Client Tool
A Python-based client for interacting with network devices using the **gNMI protocol**, supporting:
- Collection of device **capabilities**
- **Subscription** to telemetry data (streaming)

---

## Project Structure
```text
.
├── README.md
├── gnmi_c
│   ├── capabilities.py         # Handles gNMI capabilities requests
│   ├── subscribe.py            # Handles gNMI telemetry subscriptions
│   └── testbed.yaml            # Inventory file defining devices and credentials
├── gnmi_outputs                # Output from capabilities request and subscribe telemetry
│   ├── lille-core-mx10k8-1
│   │   └── capabilities.yaml
│   └── lille-core-ncs5k8-1
│       ├── capabilities.yaml
│       └── subscribe.yaml
├── main.py                     # Main entry point to run capabilities or subscribe modules
├── requirements.txt            # Python dependencies
└── utils
    ├── __init__.py
    └── helper.py               # Utilities: logging, argument parsing, YAML loader

6 directories, 12 files
```

## Clone repository
```bash
git clone <https://gitlab.com/devslearning/gnmi_interview.git>
cd <gnmi_interview>
```

## Create a virtual environment (recommended)
```bash
python3 -m venv venv
source venv/bin/activate
```

## Install dependencies
```bash
pip install -r requirements.txt
```

## testbed.yaml Overview
This YAML file defines:
- Device inventory
- Login credentials
- gNMI connection settings
- Subscription paths
``` yaml
testbed:
  name: testbed.yaml
  credentials:
    containerlab:
      username: clab
      password: clab@123

devices:
  lille-core-ncs5k8-1:
    region: containerlab
    os: iosxr
    custom:
      type: IOSXRV
      role: core_ncs5k
    connections:
      gnmi:
        host: 172.20.20.3
        port: 57400
        login_creds: containerlab
        subscriptions:
        - cisco_iosxr
  lille-core-mx10k8-1:
    region: containerlab
    os: junos
    custom:
      type: vmx
      role: core_mx10k8-1
    connections:
      gnmi:
        host: 172.20.20.4
        port: 57400
        login_creds: containerlab
        subscriptions:
        - junos_vmx
        
subscriptions:
  cisco_iosxr:
    path: openconfig-interfaces:interfaces/interface[name=MgmtEth0/RP0/CPU0/0]
    mode: sample
    sample_interval: 100000000
  junos_vmx:
    path: openconfig-interfaces:interfaces/interface/state
    mode: sample
    sample_interval: 10000000000
```

## Usage
The main.py script orchestrates execution of the different gNMI actions.
1. Get Capabilities
```bash
python main.py --testbed testbed.yaml --devices lille-core-ncs5k8-1 --action capabilities
```
Result:

A YAML file will be saved to gnmi_outputs/<device>/capabilities.yaml

2. Subscribe to Telemetry
```bash
python main.py --testbed testbed.yaml --devices lille-core-ncs5k8-1 --action subscribe
```
Result:

Subscription data will be written to gnmi_outputs/<device>/subscribe.yaml

## Command-Line Options
| Option      | Required | Description                                                  |
| ----------- | -------- | ------------------------------------------------------------ |
| `--testbed` | ✅        | Path to the testbed YAML file                                |
| `--devices` | ❌        | List of device names (space-separated). If omitted, use all. |
| `--action`  | ✅        | Action to perform: `capabilities` or `subscribe`             |

## Examples
### Multi-device capabilities collection:
```bash
python main.py --testbed testbed.yaml --devices "device1 device2" --action capabilities
```

### Run subscribe on all devices in testbed:
```bash
python main.py --testbed testbed.yaml --action subscribe
```