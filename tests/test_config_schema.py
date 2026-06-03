# =============================================================
#  Tests de configuration et de schéma (task 1.2)
# =============================================================
#
#  Tests par l'exemple (SMOKE) vérifiant l'initialisation de la
#  BaseDeDonnees : connexion, création du fichier, présence des
#  tables et de leurs colonnes, méthode fermer(), docstring de la
#  base de référence, et préservation des lignes à la réouverture.
#
#  Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 5.3, 5.4, 6.4, 6.6

import os
import sqlite3

import pytest

from classes.base_donnees import BaseDeDonnees
from _db_helpers import ouvrir_base_temporaire, faire_article, faire_resultat


# -------------------------------------------------------------
#  1.1 — Une connexion SQLite est établie à la création
# -------------------------------------------------------------
def test_connexion_etablie(tmp_path):
    base, _ = ouvrir_base_temporaire(tmp_path)
    try:
        # La connexion existe et est utilisable (une requête triviale
        # ne lève pas d'erreur).
        assert base.connexion is not None
        curseur = base.connexion.cursor()
        curseur.execute("SELECT 1")
        assert curseur.fetchone()[0] == 1
    finally:
        base.fermer()


# -------------------------------------------------------------
#  1.2 — Le fichier fakenews.db est créé sur le disque
# -------------------------------------------------------------
def test_fichier_base_cree(tmp_path):
    base, chemin = ouvrir_base_temporaire(tmp_path)
    try:
        assert os.path.isfile(chemin)
        assert os.path.basename(chemin) == "fakenews.db"
    finally:
        base.fermer()


# -------------------------------------------------------------
#  6.5 — Le dossier "data" est créé s'il n'existe pas
# -------------------------------------------------------------
def test_dossier_data_cree(tmp_path):
    base, chemin = ouvrir_base_temporaire(tmp_path)
    try:
        assert os.path.isdir(os.path.dirname(chemin))
    finally:
        base.fermer()


# -------------------------------------------------------------
#  Utilitaire : liste des tables de la base
# -------------------------------------------------------------
def _tables(base):
    curseur = base.connexion.cursor()
    curseur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return {ligne[0] for ligne in curseur.fetchall()}


# -------------------------------------------------------------
#  1.3 — La table "analyses" est présente
#  1.4 — La table "contenus_fiables" est présente
# -------------------------------------------------------------
def test_tables_presentes(tmp_path):
    base, _ = ouvrir_base_temporaire(tmp_path)
    try:
        tables = _tables(base)
        assert "analyses" in tables
        assert "contenus_fiables" in tables
    finally:
        base.fermer()


# -------------------------------------------------------------
#  1.5 — Colonnes attendues de la table "analyses" (PRAGMA)
# -------------------------------------------------------------
def test_colonnes_analyses(tmp_path):
    base, _ = ouvrir_base_temporaire(tmp_path)
    try:
        curseur = base.connexion.cursor()
        curseur.execute("PRAGMA table_info(analyses)")
        # PRAGMA table_info renvoie (cid, name, type, notnull, dflt, pk).
        colonnes = {ligne[1] for ligne in curseur.fetchall()}
        attendues = {
            "id", "titre", "contenu", "source",
            "date", "score", "verdict", "detail",
        }
        assert attendues <= colonnes
    finally:
        base.fermer()


# -------------------------------------------------------------
#  5.3 — Colonnes attendues de la table "contenus_fiables"
# -------------------------------------------------------------
def test_colonnes_contenus_fiables(tmp_path):
    base, _ = ouvrir_base_temporaire(tmp_path)
    try:
        curseur = base.connexion.cursor()
        curseur.execute("PRAGMA table_info(contenus_fiables)")
        colonnes = {ligne[1] for ligne in curseur.fetchall()}
        attendues = {"id", "titre", "contenu", "source"}
        assert attendues <= colonnes
    finally:
        base.fermer()


# -------------------------------------------------------------
#  6.4 — La méthode fermer() existe
#  6.6 — fermer() ferme effectivement la connexion active
# -------------------------------------------------------------
def test_fermer_existe_et_ferme_la_connexion(tmp_path):
    base, _ = ouvrir_base_temporaire(tmp_path)

    # 6.4 : la méthode existe et est appelable.
    assert hasattr(base, "fermer") and callable(base.fermer)

    base.fermer()

    # 6.6 : après fermeture, l'attribut connexion est remis à None
    # et toute tentative d'utiliser l'ancienne connexion échoue.
    assert base.connexion is None


def test_connexion_inutilisable_apres_fermeture(tmp_path):
    base, _ = ouvrir_base_temporaire(tmp_path)
    # On capture la connexion avant fermeture pour prouver qu'elle
    # est réellement close (et pas seulement déréférencée).
    connexion = base.connexion
    base.fermer()
    with pytest.raises(sqlite3.ProgrammingError):
        connexion.execute("SELECT 1")


# -------------------------------------------------------------
#  5.4 — La docstring de la méthode d'ajout de contenu fiable
#        mentionne l'usage futur de similarité
# -------------------------------------------------------------
def test_docstring_mentionne_similarite_future():
    doc = BaseDeDonnees.ajouter_contenu_fiable.__doc__ or ""
    doc_min = doc.lower()
    assert "similarit" in doc_min
    # Mention explicite d'un usage ultérieur / futur.
    assert ("ultérieure" in doc_min or "ulterieure" in doc_min
            or "futur" in doc_min)


# -------------------------------------------------------------
#  1.6 — Les lignes existantes sont préservées à la réouverture
#        du MÊME fichier (aucune suppression / réinitialisation)
# -------------------------------------------------------------
def test_lignes_preservees_a_la_reouverture(tmp_path):
    base, chemin = ouvrir_base_temporaire(tmp_path)
    try:
        article = faire_article(titre="Persistant")
        resultat = faire_resultat(score=77, verdict="FIABLE")
        id_cree = base.enregistrer_analyse(article, resultat)
        assert id_cree > 0
    finally:
        base.fermer()

    # Réouverture sur le même fichier : la ligne doit subsister.
    base2 = BaseDeDonnees(chemin=chemin)
    try:
        historique = base2.recuperer_historique()
        assert len(historique) == 1
        assert historique[0]["titre"] == "Persistant"
        assert historique[0]["score"] == 77
        assert historique[0]["verdict"] == "FIABLE"
    finally:
        base2.fermer()
