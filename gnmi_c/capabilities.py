"""Collecte des capabilities gNMI (version, encodages et modèles YANG supportés)."""
from __future__ import annotations

from pathlib import Path

from gnmi_c.base import GnmiTarget, GnmiTask
from utils.helper import dump_yaml


class Capabilities(GnmiTask):
    """Envoie une requête gNMI Capabilities et l'enregistre dans ``<device>/capabilities.yaml``."""

    output_filename = "capabilities.yaml"

    def run(self, target: GnmiTarget, output_file: Path) -> dict:
        with target.client() as gnmi_context:
            capabilities = gnmi_context.capabilities()

        dump_yaml({target.host: capabilities}, output_file)
        return {
            "gnmi_version": capabilities.get("gnmi_version"),
            "encodings": capabilities.get("supported_encodings", []),
            "models": len(capabilities.get("supported_models", [])),
        }
