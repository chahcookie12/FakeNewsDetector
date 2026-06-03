# =============================================================
#  Tests unitaires des erreurs d'initialisation (task 1.3)
# =============================================================
#
#  Simule les trois cas d'échec d'initialisation de BaseDeDonnees
#  et vérifie qu'une ErreurBaseDeDonnees explicite est levée.
#
#  Requirements: 1.7, 1.8, 6.5, 6.7

import sqlite3
from unittest.mock import patch, MagicMock

import pytest

from classes.base_donnees import BaseDeDonnees, ErreurBaseDeDonnees


# -------------------------------------------------------------
#  1.7 — Échec de création du schéma avec rollback
# -------------------------------------------------------------
def test_echec_schema_leve_erreur_et_rollback(tmp_path):
    """Si cursor.execute lève sqlite3.Error pendant _creer_schema,
    ErreurBaseDeDonnees est levée et le message est explicite."""

    chemin = str(tmp_path / "data" / "fakenews.db")

    # On patch sqlite3.connect pour retourner une connexion mockée
    # dont le curseur lève une erreur lors de l'exécution des CREATE TABLE.
    mock_conn = MagicMock()
    mock_curseur = MagicMock()
    mock_curseur.execute.side_effect = sqlite3.Error("disk I/O error")
    mock_conn.cursor.return_value = mock_curseur

    with patch("classes.base_donnees.sqlite3.connect", return_value=mock_conn):
        with pytest.raises(ErreurBaseDeDonnees) as exc_info:
            BaseDeDonnees(chemin=chemin)

    # Le message mentionne l'opération de création du schéma.
    message = str(exc_info.value).lower()
    assert "schéma" in message or "schema" in message or "création" in message

    # Le rollback a été appelé (atomicité).
    mock_conn.rollback.assert_called()


# -------------------------------------------------------------
#  1.8 — Connexion impossible
# -------------------------------------------------------------
def test_connexion_impossible_leve_erreur(tmp_path):
    """Si sqlite3.connect lève une erreur, ErreurBaseDeDonnees est
    levée avec un message identifiant l'opération."""

    chemin = str(tmp_path / "data" / "fakenews.db")

    with patch("classes.base_donnees.sqlite3.connect",
               side_effect=sqlite3.Error("unable to open database file")):
        with pytest.raises(ErreurBaseDeDonnees) as exc_info:
            BaseDeDonnees(chemin=chemin)

    # Le message mentionne la connexion / l'initialisation.
    message = str(exc_info.value).lower()
    assert "connexion" in message or "initialisation" in message


# -------------------------------------------------------------
#  6.7 — Échec de création du dossier "data"
# -------------------------------------------------------------
def test_echec_creation_dossier_leve_erreur(tmp_path):
    """Si os.makedirs lève OSError, ErreurBaseDeDonnees est levée
    avec un message identifiant l'opération."""

    chemin = str(tmp_path / "data" / "fakenews.db")

    with patch("classes.base_donnees.os.makedirs",
               side_effect=OSError("Permission denied")):
        with pytest.raises(ErreurBaseDeDonnees) as exc_info:
            BaseDeDonnees(chemin=chemin)

    # Le message mentionne le dossier ou l'initialisation.
    message = str(exc_info.value).lower()
    assert "dossier" in message or "initialisation" in message


# -------------------------------------------------------------
#  6.5 — Messages explicites dans tous les cas
# -------------------------------------------------------------
def test_message_explicite_schema(tmp_path):
    """Le message d'erreur du schéma contient des détails utiles."""

    chemin = str(tmp_path / "data" / "fakenews.db")

    mock_conn = MagicMock()
    mock_curseur = MagicMock()
    mock_curseur.execute.side_effect = sqlite3.Error("table malformed")
    mock_conn.cursor.return_value = mock_curseur

    with patch("classes.base_donnees.sqlite3.connect", return_value=mock_conn):
        with pytest.raises(ErreurBaseDeDonnees) as exc_info:
            BaseDeDonnees(chemin=chemin)

    # Le message contient l'erreur sous-jacente.
    message = str(exc_info.value)
    assert "table malformed" in message


def test_message_explicite_connexion(tmp_path):
    """Le message d'erreur de connexion contient des détails utiles."""

    chemin = str(tmp_path / "data" / "fakenews.db")

    with patch("classes.base_donnees.sqlite3.connect",
               side_effect=sqlite3.Error("unable to open")):
        with pytest.raises(ErreurBaseDeDonnees) as exc_info:
            BaseDeDonnees(chemin=chemin)

    message = str(exc_info.value)
    assert "unable to open" in message


def test_message_explicite_dossier(tmp_path):
    """Le message d'erreur du dossier contient des détails utiles."""

    chemin = str(tmp_path / "data" / "fakenews.db")

    with patch("classes.base_donnees.os.makedirs",
               side_effect=OSError("Permission denied")):
        with pytest.raises(ErreurBaseDeDonnees) as exc_info:
            BaseDeDonnees(chemin=chemin)

    message = str(exc_info.value)
    assert "Permission denied" in message
