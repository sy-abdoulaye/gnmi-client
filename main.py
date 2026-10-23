"""Point d'entrée du client gNMI.

Exemples :
    python main.py --testbed testbed.yaml --action capabilities
    python main.py --testbed testbed.yaml --devices lille-core-ncs5k8-1 lille-core-mx10k8-1 --action capabilities
    python main.py --testbed testbed.yaml --devices lille-core-ncs5k8-1 --action subscribe --count 10
    python main.py --testbed testbed.yaml --action subscribe --duration 60
"""
from __future__ import annotations

import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from gnmi_c.base import GnmiTask
from gnmi_c.capabilities import Capabilities
from gnmi_c.subscribe import Subscribe
from utils.helper import get_logger, load_yaml, parse_args, resolve_testbed_path, setup_logging

LOGGER = get_logger("gnmi")


def run_gnmi_task(task: GnmiTask, testbed: dict, device_names: list[str], max_workers: int = 16,
                  stop_event: threading.Event | None = None) -> list[dict]:
    """Exécute ``task`` en parallèle sur ``device_names`` et retourne un résultat par équipement.

    Un Ctrl-C positionne ``stop_event`` : les souscriptions en cours se terminent
    proprement (fichiers fermés) au lieu d'être interrompues brutalement.
    """
    results = []
    with ThreadPoolExecutor(max_workers=min(max_workers, len(device_names))) as executor:
        futures = [executor.submit(task.collect_gnmi_data, testbed, name) for name in device_names]
        try:
            for future in as_completed(futures):
                results.append(future.result())
        except KeyboardInterrupt:
            LOGGER.warning("Interruption demandée, arrêt des tâches en cours...")
            if stop_event is not None:
                stop_event.set()
            for future in futures:
                future.cancel()
            results = [f.result() for f in futures if not f.cancelled()]
    return results


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    setup_logging(args.debug)

    try:
        testbed = load_yaml(resolve_testbed_path(args.testbed)) or {}
    except Exception as error:
        LOGGER.error("Impossible de charger le testbed : %s", error)
        return 2

    device_names = args.devices or list((testbed.get("devices") or {}).keys())
    if not device_names:
        LOGGER.error("Aucun équipement à traiter")
        return 2

    stop_event = threading.Event()
    if args.action == "capabilities":
        task = Capabilities(args.output_dir)
    else:
        task = Subscribe(args.output_dir, count=args.count, duration=args.duration,
                         stop_event=stop_event)

    LOGGER.info("Action %s sur %d équipement(s) : %s", args.action, len(device_names),
                ", ".join(device_names))
    results = run_gnmi_task(task, testbed, device_names, args.max_workers, stop_event)
    LOGGER.info("Résultats gNMI :\n%s", json.dumps(results, indent=2, ensure_ascii=False))

    return 0 if all(r["status"] == "ok" for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
