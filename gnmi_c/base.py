"""Socle commun des tâches gNMI : lecture du testbed, connexion, gestion d'erreurs."""
from __future__ import annotations

import os
import re
from abc import ABC, abstractmethod
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import grpc
from pygnmi.client import gNMIclient as GnmiClient

from utils.helper import get_logger

LOGGER = get_logger(__name__)

DEFAULT_PORT = 57400
DEFAULT_ENCODING = "json"
ENV_REF = re.compile(r"^\$\{(\w+)\}$")
# Clés de connections.gnmi transmises telles quelles au client pygnmi (TLS, timeout).
CLIENT_OPTIONS = {
    "insecure": "insecure",
    "skip_verify": "skip_verify",
    "path_cert": "path_cert",
    "path_key": "path_key",
    "path_root": "path_root",
    "override": "override",
    "timeout": "gnmi_timeout",
}


class TestbedError(ValueError):
    """Le testbed ne décrit pas correctement l'équipement demandé."""


def _resolve_secret(value: Any, label: str) -> str:
    """Remplace une référence ``${VAR}`` par la variable d'environnement correspondante."""
    if value is None:
        return ""
    value = str(value)
    match = ENV_REF.match(value)
    if not match:
        return value
    env_name = match.group(1)
    if env_name not in os.environ:
        raise TestbedError(f"{label} référence la variable d'environnement {env_name}, non définie")
    return os.environ[env_name]


def _describe_error(error: Exception) -> str:
    """Message d'erreur lisible (grpc.FutureTimeoutError n'a pas de message propre)."""
    if isinstance(error, grpc.FutureTimeoutError):
        return "connexion gNMI impossible : délai dépassé (équipement injoignable ?)"
    if isinstance(error, grpc.RpcError) and hasattr(error, "code"):
        return f"erreur gRPC {error.code().name} : {error.details()}"
    return f"{type(error).__name__}: {error}"


@dataclass(frozen=True)
class GnmiTarget:
    """Paramètres de connexion gNMI d'un équipement, extraits et validés depuis le testbed."""

    name: str
    host: str
    port: int
    username: str
    password: str = field(repr=False)
    encoding: str = DEFAULT_ENCODING
    subscriptions: list[dict] = field(default_factory=list)
    client_options: dict = field(default_factory=dict)

    @classmethod
    def from_testbed(cls, testbed: dict, device_name: str) -> GnmiTarget:
        """Construit la cible ``device_name`` ; lève TestbedError si le testbed est incomplet."""
        device = (testbed.get("devices") or {}).get(device_name)
        if device is None:
            raise TestbedError(f"équipement absent du testbed : {device_name}")

        gnmi = (device.get("connections") or {}).get("gnmi")
        if not gnmi or not gnmi.get("host"):
            raise TestbedError(f"{device_name} : connections.gnmi.host manquant")

        creds_name = gnmi.get("login_creds")
        credentials = ((testbed.get("testbed") or {}).get("credentials") or {})
        creds = credentials.get(creds_name)
        if creds is None:
            raise TestbedError(f"{device_name} : credentials '{creds_name}' introuvables")

        sensors = testbed.get("subscriptions") or {}
        subscriptions = []
        for sub_name in gnmi.get("subscriptions") or []:
            if sub_name not in sensors:
                raise TestbedError(f"{device_name} : subscription '{sub_name}' non définie")
            # Copie : pygnmi peut modifier le dictionnaire de requête.
            subscriptions.append(deepcopy(sensors[sub_name]))

        client_options = {"insecure": True}
        for key, option in CLIENT_OPTIONS.items():
            if key in gnmi:
                client_options[option] = gnmi[key]

        return cls(
            name=device_name,
            host=str(gnmi["host"]),
            port=int(gnmi.get("port", DEFAULT_PORT)),
            username=_resolve_secret(creds.get("username"), f"{creds_name}.username"),
            password=_resolve_secret(creds.get("password"), f"{creds_name}.password"),
            encoding=gnmi.get("encoding", DEFAULT_ENCODING),
            subscriptions=subscriptions,
            client_options=client_options,
        )

    def client(self, **extra: Any) -> GnmiClient:
        """Retourne un client pygnmi (à utiliser comme gestionnaire de contexte)."""
        return GnmiClient(
            target=(self.host, self.port),
            username=self.username,
            password=self.password,
            **{**self.client_options, **extra},
        )


class GnmiTask(ABC):
    """Tâche gNMI exécutée équipement par équipement (une instance partagée entre threads).

    Les sous-classes définissent ``output_filename`` et implémentent ``run``.
    """

    output_filename: str = ""

    def __init__(self, output_dir: str | Path = "gnmi_outputs"):
        self.output_dir = Path(output_dir)

    def collect_gnmi_data(self, testbed: dict, device_name: str) -> dict:
        """Exécute la tâche pour un équipement sans jamais lever d'exception.

        Returns:
            dict: ``device``, ``host``, ``status`` (``ok`` ou ``error``), puis
            ``output`` et les compteurs de la tâche, ou ``error``.
        """
        result = {"device": device_name, "host": None}
        try:
            target = GnmiTarget.from_testbed(testbed, device_name)
            result["host"] = f"{target.host}:{target.port}"
            output_file = self.output_dir / device_name / self.output_filename
            output_file.parent.mkdir(parents=True, exist_ok=True)

            LOGGER.info("%s : connexion à %s", device_name, result["host"])
            result.update(self.run(target, output_file) or {})
            result.update(status="ok", output=str(output_file))
        except Exception as error:  # un équipement en échec ne doit pas arrêter les autres
            message = _describe_error(error)
            LOGGER.error("%s : %s", device_name, message)
            result.update(status="error", error=message)
        return result

    @abstractmethod
    def run(self, target: GnmiTarget, output_file: Path) -> dict | None:
        """Interroge ``target`` et écrit le résultat dans ``output_file``."""
