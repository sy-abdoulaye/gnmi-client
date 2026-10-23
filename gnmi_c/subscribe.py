"""Souscription télémétrie gNMI en mode STREAM."""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import grpc
import yaml

from gnmi_c.base import GnmiTarget, GnmiTask
from utils.helper import get_logger

LOGGER = get_logger(__name__)

# Délai d'attente d'une notification : borne la réactivité à l'arrêt (Ctrl-C, --duration).
POLL_INTERVAL = 1.0
# La première notification fusionne toutes les mises à jour jusqu'au sync_response :
# on lui laisse plus de temps pour ne pas perdre l'instantané initial.
FIRST_UPDATE_TIMEOUT = 30.0


def _ignore_cancelled_streams(args: threading.ExceptHookArgs) -> None:
    """Masque l'exception CANCELLED levée par le thread interne de pygnmi à la fermeture du canal.

    C'est l'issue normale d'une souscription que l'on arrête ; les autres
    erreurs passent au gestionnaire par défaut (et remontent via subscriber.error).
    """
    if isinstance(args.exc_value, grpc.RpcError) and \
            getattr(args.exc_value, "code", lambda: None)() == grpc.StatusCode.CANCELLED:
        return
    _default_excepthook(args)


_default_excepthook = threading.excepthook
threading.excepthook = _ignore_cancelled_streams


class Subscribe(GnmiTask):
    """Souscrit aux capteurs du testbed et écrit chaque notification dans ``<device>/subscribe.yaml``.

    Le fichier est un flux YAML multi-documents (un document ``---`` par
    notification), écrit au fil de l'eau. La souscription s'arrête après
    ``count`` notifications, après ``duration`` secondes, ou quand
    ``stop_event`` est positionné (Ctrl-C dans main.py).
    """

    output_filename = "subscribe.yaml"

    def __init__(self, output_dir="gnmi_outputs", count: int | None = None,
                 duration: float | None = None, stop_event: threading.Event | None = None):
        super().__init__(output_dir)
        self.count = count
        self.duration = duration
        self.stop_event = stop_event or threading.Event()

    @staticmethod
    def build_request(target: GnmiTarget) -> dict:
        """Construit la requête SubscribeRequest (format pygnmi) à partir des capteurs de l'équipement."""
        if not target.subscriptions:
            raise ValueError("aucune subscription définie dans connections.gnmi.subscriptions")
        return {
            "subscription": target.subscriptions,
            "mode": "stream",
            "encoding": target.encoding,
        }

    def run(self, target: GnmiTarget, output_file: Path) -> dict:
        request = self.build_request(target)
        deadline = time.monotonic() + self.duration if self.duration else None
        received = 0

        with target.client(no_qos_marking=True) as gnmi_context, \
                open(output_file, "w", encoding="utf-8") as f:
            subscriber = gnmi_context.subscribe2(subscribe=request)
            try:
                while not self.stop_event.is_set():
                    if deadline is not None and time.monotonic() >= deadline:
                        break
                    timeout = FIRST_UPDATE_TIMEOUT if received == 0 else POLL_INTERVAL
                    try:
                        notification = subscriber.get_update(timeout=timeout)
                    except TimeoutError:
                        if subscriber.error:
                            raise subscriber.error
                        continue

                    yaml.safe_dump({target.host: notification}, f, explicit_start=True,
                                   default_flow_style=False, sort_keys=False)
                    f.flush()
                    received += 1
                    self._log_notification(target.name, received, notification)
                    if self.count is not None and received >= self.count:
                        break
            finally:
                subscriber.close()

        return {"notifications": received}

    @staticmethod
    def _log_notification(device: str, index: int, notification: dict) -> None:
        update = notification.get("update", {})
        LOGGER.info("%s : notification #%d (prefix=%r, %d valeur(s))", device, index,
                    update.get("prefix", ""), len(update.get("update", [])))
        LOGGER.debug("%s : %s", device, json.dumps(notification, indent=2, default=str))
