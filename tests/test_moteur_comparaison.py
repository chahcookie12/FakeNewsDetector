# =============================================================
#  test_moteur_comparaison.py
#  Tests unitaires — MoteurSimilarite : comparaison cosinus et
#  calcul des pourcentages (tâche 4.2)
# =============================================================
#
#  Ces tests couvrent UNIQUEMENT le périmètre de la tâche 4.2 :
#    - vectorisation de l'article entrant + similarité cosinus
#      avec chaque article de référence (exigence 5.3) ;
#    - conversion en pourcentage borné [0, 100] (exigence 5.5) ;
#    - auto-similarité : un contenu identique à une référence
#      obtient un pourcentage ≥ 99 % (exigence 5.6) ;
#    - vecteur TF-IDF nul (texte vide / hors vocabulaire) : aucune
#      correspondance (exigence 9.5).
#
#  La sélection / le tri (tâche 4.5) et l'ajustement de score
#  (tâche 4.7) ne sont PAS testés ici.
#
#  Les tests nécessitant scikit-learn sont ignorés (skip) si la
#  dépendance optionnelle est absente (dégradation gracieuse).

import pytest

from classes.article import Article
from classes.moteur_similarite import MoteurSimilarite, SKLEARN_DISPONIBLE

from _db_helpers import ouvrir_base_temporaire


# Skip conditionnel : sans scikit-learn, ces tests sont ignorés.
besoin_sklearn = pytest.mark.skipif(
    not SKLEARN_DISPONIBLE,
    reason="scikit-learn n'est pas installé (dépendance optionnelle)",
)


def _base_avec_references(tmp_path):
    """Ouvre une base temporaire alimentée de quelques articles de
    référence distincts, et la retourne."""
    base, _ = ouvrir_base_temporaire(tmp_path)
    base.ajouter_article_reference(
        "Vaccins", "les vaccins protegent contre les maladies graves", "real"
    )
    base.ajouter_article_reference(
        "Complot", "la terre est plate selon une theorie du complot", "fake"
    )
    base.ajouter_article_reference(
        "Economie", "la bourse et les marches financiers en hausse", "real"
    )
    return base


# -------------------------------------------------------------
#  Bornes des pourcentages (exigence 5.5)
# -------------------------------------------------------------

@besoin_sklearn
def test_pourcentages_alignes_et_bornes(tmp_path):
    """Chaque pourcentage retourné est aligné avec la référence et
    se trouve dans l'intervalle [0, 100]."""
    base = _base_avec_references(tmp_path)
    try:
        moteur = MoteurSimilarite(base)
        article = Article("Sante", "les vaccins protegent les maladies", None)

        pourcentages = moteur._calculer_pourcentages(article)

        # Un pourcentage par article de référence (alignement).
        assert len(pourcentages) == len(moteur._articles_reference)
        # Toutes les valeurs sont bien bornées dans [0, 100].
        for valeur in pourcentages:
            assert 0.0 <= valeur <= 100.0
    finally:
        base.fermer()


@besoin_sklearn
def test_clamp_haut_via_pourcentage_borne():
    """_pourcentage_borne ramène un dépassement (>1) à 100 et une
    valeur négative à 0 (clamp [0, 100])."""
    # Le moteur n'a pas besoin de base pour ce test unitaire ciblé.
    moteur = MoteurSimilarite(None)
    assert moteur._pourcentage_borne(1.0) == 100.0
    assert moteur._pourcentage_borne(1.0000001) == 100.0
    assert moteur._pourcentage_borne(-0.5) == 0.0
    assert moteur._pourcentage_borne(0.5) == 50.0


# -------------------------------------------------------------
#  Auto-similarité (exigence 5.6)
# -------------------------------------------------------------

@besoin_sklearn
def test_auto_similarite_contenu_identique(tmp_path):
    """Un article au contenu identique à une référence obtient un
    pourcentage ≥ 99 % sur la ligne correspondante."""
    base = _base_avec_references(tmp_path)
    try:
        moteur = MoteurSimilarite(base)

        # Le corpus de référence est construit à partir du seul champ
        # "contenu" de chaque Article_Reference. Pour reproduire une
        # auto-similarité, le texte comparable de l'article entrant
        # doit donc être IDENTIQUE à ce contenu de référence : on
        # laisse le titre vide pour que _extraire_texte ne renvoie
        # que le contenu.
        article = Article(
            "", "la terre est plate selon une theorie du complot", None
        )

        pourcentages = moteur._calculer_pourcentages(article)

        # Il existe au moins une référence avec ≥ 99 % (l'identique).
        assert max(pourcentages) >= 99.0
    finally:
        base.fermer()


# -------------------------------------------------------------
#  Vecteur TF-IDF nul (exigence 9.5)
# -------------------------------------------------------------

@besoin_sklearn
def test_vecteur_nul_texte_vide(tmp_path):
    """Un article au texte vide produit un vecteur TF-IDF nul :
    aucune correspondance (liste vide)."""
    base = _base_avec_references(tmp_path)
    try:
        moteur = MoteurSimilarite(base)
        article = Article("", "", None)
        assert moteur._calculer_pourcentages(article) == []
    finally:
        base.fermer()


@besoin_sklearn
def test_vecteur_nul_hors_vocabulaire(tmp_path):
    """Un article dont aucun terme n'appartient au vocabulaire de
    référence produit un vecteur nul : aucune correspondance."""
    base = _base_avec_references(tmp_path)
    try:
        moteur = MoteurSimilarite(base)
        # Termes absents du vocabulaire de référence.
        article = Article("zzzqqq", "xkcdfoo wibblewobble", None)
        assert moteur._calculer_pourcentages(article) == []
    finally:
        base.fermer()
