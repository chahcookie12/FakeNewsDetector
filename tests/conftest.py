# =============================================================
#  conftest.py — configuration partagée des tests
# =============================================================
#
#  pytest charge ce fichier AVANT de collecter les modules de
#  test. On en profite pour garantir que la racine du projet
#  (qui contient le paquet "classes") est sur le sys.path, afin
#  que les tests puissent faire "from classes.base_donnees ...".
#
#  Le dossier "tests/" lui-même est ajouté au sys.path par pytest
#  (mode d'import "prepend"), ce qui permet d'importer le module
#  d'aide "_db_helpers".

import os
import sys

# Racine du projet = dossier parent de "tests/".
_RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RACINE not in sys.path:
    sys.path.insert(0, _RACINE)
