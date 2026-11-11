# =============================================================
#  Tests unitaires de validation d'enregistrement de référence
#  (task 1.4)
# =============================================================
#
#  Vérifie le contrat de ajouter_article_reference :
#    - rejet d'un label invalide (ErreurBaseDeDonnees, aucune
#      ligne écrite) ;
#    - rejet d'un titre ou d'un contenu vide / espaces (aucune
#      ligne écrite) ;
#    - normalisation d'une source absente (None / vide / espaces)
#      en "Inconnue".
#
#  Style aligné sur test_enregistrement_erreurs.py :
#  pytest.raises(ErreurBaseDeDonnees) + comptage des lignes via
#  SELECT COUNT(*) sur une base SQLite temporaire isolée.
#
#  Requirements: 4.2, 4.3, 4.5

import pytest

from classes.base_donnees import ErreurBaseDeDonnees
from _db_helpers import ouvrir_base_temporaire


# -------------------------------------------------------------
#  Utilitaire local : nombre de lignes dans articles_reference
# -------------------------------------------------------------
def _compter_lignes(base):
    """Compte directement les lignes de la table articles_reference
    via SQL (indépendant des méthodes métier de la classe)."""
    curseur = base.connexion.cursor()
    curseur.execute("SELECT COUNT(*) FROM articles_reference")
    return curseur.fetchone()[0]


# -------------------------------------------------------------
#  4.2 — Label invalide -> ErreurBaseDeDonnees, aucune ligne
# -------------------------------------------------------------
@pytest.mark.parametrize(
    "label_invalide",
    ["FAKE", "Real", "true", "vrai", "", " ", "fakenews", None],
)
def test_label_invalide_rejete_sans_ecriture(tmp_path, label_invalide):
    """Un label hors de {'fake', 'real'} est rejeté avec
    ErreurBaseDeDonnees et n'écrit aucune ligne."""

    base, _ = ouvrir_base_temporaire(tmp_path)
    try:
        with pytest.raises(ErreurBaseDeDonnees):
            base.ajouter_article_reference(
                titre="Un titre",
                contenu="Un contenu",
                label=label_invalide,
            )

        assert _compter_lignes(base) == 0, (
            "Aucune ligne ne doit être écrite pour un label invalide"
        )
    finally:
        base.fermer()


def test_message_label_invalide_identifie_etiquette(tmp_path):
    """Le message d'erreur mentionne l'étiquette invalide."""

    base, _ = ouvrir_base_temporaire(tmp_path)
    try:
        with pytest.raises(ErreurBaseDeDonnees) as exc_info:
            base.ajouter_article_reference("T", "C", label="invalide")

        message = str(exc_info.value).lower()
        assert "étiquette" in message or "etiquette" in message or "label" in message
    finally:
        base.fermer()


# -------------------------------------------------------------
#  4.3 — Titre vide -> ErreurBaseDeDonnees, aucune ligne
# -------------------------------------------------------------
@pytest.mark.parametrize("titre_vide", ["", " ", "   ", "\t", "\n", " \t \n ", None])
def test_titre_vide_rejete_sans_ecriture(tmp_path, titre_vide):
    """Un titre vide / composé uniquement d'espaces (ou None) est
    rejeté et n'écrit aucune ligne."""

    base, _ = ouvrir_base_temporaire(tmp_path)
    try:
        with pytest.raises(ErreurBaseDeDonnees):
            base.ajouter_article_reference(
                titre=titre_vide,
                contenu="Un contenu valide",
                label="fake",
            )

        assert _compter_lignes(base) == 0, (
            "Aucune ligne ne doit être écrite pour un titre vide"
        )
    finally:
        base.fermer()


# -------------------------------------------------------------
#  4.3 — Contenu vide -> ErreurBaseDeDonnees, aucune ligne
# -------------------------------------------------------------
@pytest.mark.parametrize("contenu_vide", ["", " ", "   ", "\t", "\n", " \t \n ", None])
def test_contenu_vide_rejete_sans_ecriture(tmp_path, contenu_vide):
    """Un contenu vide / composé uniquement d'espaces (ou None) est
    rejeté et n'écrit aucune ligne."""

    base, _ = ouvrir_base_temporaire(tmp_path)
    try:
        with pytest.raises(ErreurBaseDeDonnees):
            base.ajouter_article_reference(
                titre="Un titre valide",
                contenu=contenu_vide,
                label="real",
            )

        assert _compter_lignes(base) == 0, (
            "Aucune ligne ne doit être écrite pour un contenu vide"
        )
    finally:
        base.fermer()


# -------------------------------------------------------------
#  4.5 — Source absente -> normalisée en "Inconnue"
# -------------------------------------------------------------
@pytest.mark.parametrize("source_absente", [None, "", " ", "   ", "\t", "\n", " \t \n "])
def test_source_absente_normalisee_en_inconnue(tmp_path, source_absente):
    """Une source nulle, vide ou composée uniquement d'espaces est
    conservée avec la valeur 'Inconnue'."""

    base, _ = ouvrir_base_temporaire(tmp_path)
    try:
        id_cree = base.ajouter_article_reference(
            titre="Un titre",
            contenu="Un contenu",
            label="fake",
            source=source_absente,
        )
        assert isinstance(id_cree, int) and id_cree > 0

        curseur = base.connexion.cursor()
        curseur.execute(
            "SELECT source FROM articles_reference WHERE id = ?", (id_cree,)
        )
        source_stockee = curseur.fetchone()[0]
        assert source_stockee == "Inconnue"
    finally:
        base.fermer()


def test_source_absente_par_defaut_normalisee(tmp_path):
    """Sans argument source (valeur par défaut None), la source est
    normalisée en 'Inconnue'."""

    base, _ = ouvrir_base_temporaire(tmp_path)
    try:
        id_cree = base.ajouter_article_reference(
            titre="Un titre",
            contenu="Un contenu",
            label="real",
        )

        curseur = base.connexion.cursor()
        curseur.execute(
            "SELECT source FROM articles_reference WHERE id = ?", (id_cree,)
        )
        assert curseur.fetchone()[0] == "Inconnue"
    finally:
        base.fermer()


# -------------------------------------------------------------
#  4.5 — Source présente -> conservée telle quelle
# -------------------------------------------------------------
def test_source_presente_conservee(tmp_path):
    """Une source non vide est conservée sans modification."""

    base, _ = ouvrir_base_temporaire(tmp_path)
    try:
        id_cree = base.ajouter_article_reference(
            titre="Un titre",
            contenu="Un contenu",
            label="fake",
            source="politicsNews",
        )

        curseur = base.connexion.cursor()
        curseur.execute(
            "SELECT source FROM articles_reference WHERE id = ?", (id_cree,)
        )
        assert curseur.fetchone()[0] == "politicsNews"
    finally:
        base.fermer()
