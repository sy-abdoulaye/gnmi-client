# Client gNMI

Client Python ([pygnmi](https://github.com/akarneliuk/pygnmi)) pour interroger des équipements réseau via le protocole **gNMI** :

- **Capabilities** : version gNMI, encodages et modèles YANG supportés par l'équipement ;
- **Subscribe** : souscription télémétrie en mode `STREAM` (capteurs définis dans le testbed).

Les équipements sont traités **en parallèle** (un thread par équipement) ; une erreur sur l'un n'interrompt pas les autres.

---

## Structure du projet

```text
.
├── main.py                 # Point d'entrée CLI : charge le testbed et orchestre les tâches
├── gnmi_c/
│   ├── base.py             # GnmiTarget (lecture/validation du testbed) + GnmiTask (socle commun)
│   ├── capabilities.py     # Tâche Capabilities
│   ├── subscribe.py        # Tâche Subscribe (flux STREAM)
│   └── testbed.yaml        # Inventaire : équipements, identifiants, capteurs
├── gnmi_outputs/           # Résultats, un dossier par équipement
│   └── <device>/
│       ├── capabilities.yaml
│       └── subscribe.yaml
├── utils/
│   └── helper.py           # Journalisation, arguments CLI, lecture/écriture YAML
└── requirements.txt
```

## Installation

```bash
git clone https://gitlab.com/devslearning/gnmi_interview.git
cd gnmi_interview
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Python 3.8 ou plus récent.

## Le fichier testbed

Le testbed décrit l'inventaire, les identifiants, les paramètres de connexion gNMI et les capteurs de télémétrie.

```yaml
testbed:
  name: testbed.yaml
  credentials:
    containerlab:
      username: clab
      password: clab@123          # ou "${GNMI_PASSWORD}" pour lire une variable d'environnement

devices:
  lille-core-ncs5k8-1:
    os: iosxr
    connections:
      gnmi:
        host: 172.20.20.3
        port: 57400               # défaut : 57400
        login_creds: containerlab # clé dans testbed.credentials
        subscriptions:            # clés dans la section subscriptions
        - cisco_iosxr

subscriptions:
  cisco_iosxr:
    path: openconfig-interfaces:interfaces/interface[name=MgmtEth0/RP0/CPU0/0]
    mode: sample
    sample_interval: 100000000    # en nanosecondes (ici 100 ms)
```

### Paramètres de `connections.gnmi`

| Clé | Défaut | Rôle |
| --- | --- | --- |
| `host` | — (obligatoire) | Adresse de l'équipement |
| `port` | `57400` | Port gNMI |
| `login_creds` | — (obligatoire) | Jeu d'identifiants de `testbed.credentials` |
| `subscriptions` | `[]` | Capteurs de la section `subscriptions` (requis pour `subscribe`) |
| `encoding` | `json` | Encodage demandé (`json`, `json_ietf`, `proto`…) |
| `insecure` | `true` | Connexion gRPC sans TLS (cas de containerlab) |
| `skip_verify` | — | TLS sans vérification du certificat |
| `path_cert`, `path_key`, `path_root` | — | Certificats pour une connexion TLS |
| `override` | — | Nom d'hôte attendu dans le certificat |
| `timeout` | `5` | Délai de connexion en secondes |

### Secrets

Un `username` ou `password` de la forme `${NOM_VARIABLE}` est remplacé par la variable d'environnement correspondante, ce qui évite de versionner les mots de passe :

```bash
export GNMI_PASSWORD='...'
```

Si la variable n'est pas définie, l'équipement est marqué en erreur avec un message explicite.

## Utilisation

```bash
python main.py --testbed testbed.yaml --action <capabilities|subscribe> [options]
```

`--testbed` accepte un chemin direct ou un nom de fichier situé dans `gnmi_c/`.

### Capabilities

```bash
python main.py --testbed testbed.yaml --devices lille-core-ncs5k8-1 --action capabilities
```

Le résultat complet est écrit dans `gnmi_outputs/<device>/capabilities.yaml` ; le résumé final indique la version gNMI, les encodages et le nombre de modèles YANG.

### Subscribe

```bash
# Flux continu, arrêt par Ctrl-C
python main.py --testbed testbed.yaml --devices lille-core-ncs5k8-1 --action subscribe

# Arrêt après 10 notifications par équipement
python main.py --testbed testbed.yaml --action subscribe --count 10

# Arrêt après 60 secondes
python main.py --testbed testbed.yaml --action subscribe --duration 60
```

Chaque notification est ajoutée au fil de l'eau dans `gnmi_outputs/<device>/subscribe.yaml`, sous forme de flux YAML multi-documents (un document `---` par notification). La première notification regroupe l'instantané initial jusqu'au `sync_response` de l'équipement.

Lecture du fichier en Python :

```python
import yaml
with open("gnmi_outputs/lille-core-ncs5k8-1/subscribe.yaml") as f:
    for notification in yaml.safe_load_all(f):
        ...
```

Un Ctrl-C arrête proprement toutes les souscriptions (fichiers fermés, résumé affiché).

## Options de la ligne de commande

| Option | Obligatoire | Description |
| --- | --- | --- |
| `--testbed` | oui | Fichier testbed YAML |
| `--action` | oui | `capabilities` ou `subscribe` |
| `--devices` | non | Équipements ciblés, séparés par des espaces (`--devices r1 r2` ou `--devices "r1 r2"`). Par défaut : tous. |
| `--output-dir` | non | Répertoire de sortie (défaut : `gnmi_outputs`) |
| `--count` | non | `subscribe` : nombre de notifications par équipement avant arrêt |
| `--duration` | non | `subscribe` : durée en secondes avant arrêt |
| `--max-workers` | non | Équipements traités en parallèle (défaut : 16) |
| `--debug` | non | Journalisation détaillée (chaque notification en JSON) |

## Résultat et code de sortie

En fin d'exécution, un résumé JSON est journalisé, une entrée par équipement :

```json
{
  "device": "lille-core-ncs5k8-1",
  "host": "172.20.20.3:57400",
  "notifications": 10,
  "status": "ok",
  "output": "gnmi_outputs/lille-core-ncs5k8-1/subscribe.yaml"
}
```

En cas d'échec, `status` vaut `error` et `error` donne la cause (équipement absent du testbed, identifiants introuvables, équipement injoignable, erreur gRPC…).

| Code | Signification |
| --- | --- |
| `0` | Tous les équipements ont réussi |
| `1` | Au moins un équipement en erreur |
| `2` | Testbed illisible ou aucun équipement à traiter |

## Ajouter une action gNMI

1. Créer une classe héritant de `GnmiTask` (`gnmi_c/base.py`) ;
2. définir `output_filename` et implémenter `run(target, output_file)`, qui utilise `target.client()` et retourne un dictionnaire de compteurs pour le résumé ;
3. ajouter l'action dans `ACTIONS` (`utils/helper.py`) et dans `main()`.

La lecture du testbed, la création du dossier de sortie, la gestion des erreurs et l'exécution parallèle sont prises en charge par le socle commun.
