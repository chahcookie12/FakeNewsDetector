# =============================================================
#  Tests unitaires des erreurs d'enregistrement (task 2.4)
# =============================================================
#
#  Vérifie le comportement de enregistrer_analyse en cas d'échec :
#  rollback, aucune ligne résiduelle, aucun id retourné, message
#  identifiant l'opération, et récupérabilité (fichier verrouillé).
#
#  Requirements: 2.5, 2.8, 6.1, 6.2, 6.3

import sqlite3
from unittest.mock import patch, MagicMock

import pytest

from classes.base_donnees import BaseDeDonnees, ErreurBaseDeDonnees
from _db_helpers import ouvrir_base_temporaire, faire_article, faire_resultat


# -------------------------------------------------------------
#  2.5, 2.8, 6.3 — Échec → rollback, pas de ligne, pas d'id
# -------------------------------------------------------------
def test_echec_enregistrement_rollback_pas_de_ligne(tmp_path):
    """Un échec d'INSERT déclenche un rollback, ne laisse aucune
    ligne résiduelle et ne retourne aucun identifiant."""

    base, chemin = ouvrir_base_temporaire(tmp_path)
    article = faire_article()
    resultat = faire_resultat()

    try:
        # On remplace la connexion par un mock qui lève une erreur sur
        # cursor().execute("INSERT..."). On garde la vraie connexion pour
        # vérifier ensuite que la table est vide.
        real_conn = base.connexion

        mock_conn = MagicMock()
        mock_curseur = MagicMock()
        mock_curseur.execute.side_effect = sqlite3.Error("simulated write failure")
        mock_conn.cursor.return_value = mock_curseur

        base.connexion = mock_conn

        with pytest.raises(ErreurBaseDeDonnees):
            base.enregistrer_analyse(article, resultat)

        # Le rollback a été appelé.
        mock_conn.rollback.assert_called()

        # Restaurer la vraie connexion pour vérification.
        base.connexion = real_conn

        # Vérification : la table est vide (rien n'a été écrit).
        curseur = base.connexion.cursor()
        curseur.execute("SELECT COUNT(*) FROM analyses")
        count = curseur.fetchone()[0]
        assert count == 0, "Aucune ligne résiduelle ne doit subsister"
    finally:
        base.fermer()


# -------------------------------------------------------------
#  6.1 — Le message d'erreur identifie l'opération
# -------------------------------------------------------------
def test_message_erreur_identifie_operation(tmp_path):
    """Le message d'ErreurBaseDeDonnees contient 'enregistrement'
    ou 'Enregistrement' pour identifier l'opération échouée."""

    base, _ = ouvrir_base_temporaire(tmp_path)
    article = faire_article()
    resultat = faire_resultat()

    try:
        # Remplacer la connexion par un mock pour provoquer l'erreur.
        mock_conn = MagicMock()
        mock_curseur = MagicMock()
        mock_curseur.execute.side_effect = sqlite3.Error("write error")
        mock_conn.cursor.return_value = mock_curseur

        base.connexion = mock_conn

        with pytest.raises(ErreurBaseDeDonnees) as exc_info:
            base.enregistrer_analyse(article, resultat)

        message = str(exc_info.value)
        assert ("enregistrement" in message.lower()), (
            f"Le message doit mentionner l'opération : {message}"
        )
    finally:
        base.fermer()


# -------------------------------------------------------------
#  6.2 — Fichier verrouillé = erreur récupérable, pas de crash
# -------------------------------------------------------------
def test_fichier_verrouille_erreur_recuperable(tmp_path):
    """Un fichier verrouillé par une autre connexion lève
    ErreurBaseDeDonnees (pas un crash) et la base reste utilisable."""

    base, chemin = ouvrir_base_temporaire(tmp_path)
    article = faire_article()
    resultat = faire_resultat()

    try:
        # Ouvrir une seconde connexion et prendre un verrou exclusif.
        conn2 = sqlite3.connect(chemin)
        conn2.execute("BEGIN EXCLUSIVE")

        # L'enregistrement doit échouer avec ErreurBaseDeDonnees.
        # On réduit le timeout de la connexion principale pour ne pas
        # attendre trop longtemps (par défaut 5s).
        base.connexion.execute("PRAGMA busy_timeout = 50")

        with pytest.raises(ErreurBaseDeDonnees):
            base.enregistrer_analyse(article, resultat)

        # Libérer le verrou.
        conn2.rollback()
        conn2.close()

        # La base est toujours utilisable après l'erreur (récupérable).
        # On peut enregistrer normalement maintenant que le verrou est
        # libéré.
        id_ok = base.enregistrer_analyse(article, resultat)
        assert id_ok > 0, "La base est toujours utilisable après l'erreur"
    finally:
        base.fermer()
