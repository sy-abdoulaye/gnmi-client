"""Utilitaires partagés : journalisation, arguments CLI, lecture/écriture YAML."""
from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Any

import yaml

LOG_FORMAT = "%(asctime)s %(name)s-%(levelname)s: %(message)s"
LOG_DATEFMT = "%Y-%m-%d %H:%M:%S"
ACTIONS = ("capabilities", "subscribe")
DEFAULT_TESTBED_DIR = Path(__file__).resolve().parent.parent / "gnmi_c"


def setup_logging(debug: bool = False) -> None:
    """Configure le logger racine une seule fois, depuis le point d'entrée."""
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format=LOG_FORMAT,
        datefmt=LOG_DATEFMT,
        force=True,
    )
    # grpc/pygnmi sont très bavards en DEBUG : on ne garde que nos messages.
    for noisy in ("grpc", "pygnmi"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Retourne un logger nommé (la configuration est faite par setup_logging)."""
    return logging.getLogger(name)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Analyse la ligne de commande.

    ``--devices`` accepte des noms séparés par des espaces, en plusieurs
    arguments (``--devices r1 r2``) ou dans une seule chaîne (``--devices "r1 r2"``).
    """
    parser = argparse.ArgumentParser(
        description="Client gNMI : collecte des capabilities et souscription télémétrie.",
    )
    parser.add_argument("--testbed", required=True,
                        help="Fichier testbed YAML (chemin direct, ou nom relatif à gnmi_c/).")
    parser.add_argument("--action", required=True, choices=ACTIONS,
                        help="Action gNMI à exécuter.")
    parser.add_argument("--devices", nargs="+", default=None,
                        help="Équipements ciblés (par défaut : tous ceux du testbed).")
    parser.add_argument("--output-dir", default="gnmi_outputs",
                        help="Répertoire de sortie (défaut : gnmi_outputs).")
    parser.add_argument("--count", type=int, default=None,
                        help="subscribe : arrêt après N notifications par équipement.")
    parser.add_argument("--duration", type=float, default=None,
                        help="subscribe : arrêt après N secondes.")
    parser.add_argument("--max-workers", type=int, default=16,
                        help="Nombre maximal d'équipements traités en parallèle (défaut : 16).")
    parser.add_argument("--debug", action="store_true",
                        help="Journalisation DEBUG (affiche chaque notification en JSON).")
    args = parser.parse_args(argv)

    if args.devices:
        args.devices = [name for chunk in args.devices for name in chunk.split()]
    for opt in ("count", "duration", "max_workers"):
        value = getattr(args, opt)
        if value is not None and value <= 0:
            parser.error(f"--{opt.replace('_', '-')} doit être strictement positif")
    return args


def resolve_testbed_path(testbed: str) -> Path:
    """Retourne le chemin du testbed.

    Le chemin fourni est utilisé tel quel s'il existe ; sinon il est cherché
    dans ``gnmi_c/`` (compatibilité avec ``--testbed testbed.yaml``).
    """
    path = Path(testbed)
    if path.is_file():
        return path
    fallback = DEFAULT_TESTBED_DIR / testbed
    if fallback.is_file():
        return fallback
    raise FileNotFoundError(f"testbed introuvable : {testbed} (ni {fallback})")


def load_yaml(file_path: str | Path) -> Any:
    """Charge un fichier YAML avec le chargeur sûr (aucun objet Python arbitraire)."""
    with open(file_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def dump_yaml(data: Any, file_path: str | Path) -> None:
    """Écrit ``data`` dans un fichier YAML lisible (ordre des clés conservé)."""
    with open(file_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
