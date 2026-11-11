# =============================================================
#  test_moteur_disponibilite.py
#  Tests unitaires — MoteurSimilarite : détection de dépendance
#  et cycle de vie du modèle (tâche 4.1)
# =============================================================
#
#  Ces tests couvrent UNIQUEMENT le périmètre de la tâche 4.1 :
#    - est_disponible() renvoie False sans scikit-learn ou sur
#      référence vide (exigences 9.1, 9.2) ;
#    - le modèle TF-IDF est construit une seule fois puis mis en
#      cache (exigences 5.1, 5.2) ;
#    - invalider_cache() force la reconstruction (exigence 5.4).
#
#  Les tests qui nécessitent scikit-learn sont automatiquement
#  ignorés (skip) si la dépendance optionnelle est absente, afin
#  de respecter la dégradation gracieuse.

import pytest

from classes import moteur_similarite
from classes.moteur_similarite import MoteurSimilarite, SKLEARN_DISPONIBLE

from _db_helpers import ouvrir_base_temporaire


# Skip conditionnel : les tests de construction du modèle exigent
# scikit-learn. Sans la dépendance, ils sont ignorés proprement.
besoin_sklearn = pytest.mark.skipif(
    not SKLEARN_DISPONIBLE,
    reason="scikit-learn n'est pas installé (dépendance optionnelle)",
)


# -------------------------------------------------------------
#  Détection de dépendance et référence vide (9.1, 9.2)
# -------------------------------------------------------------

def test_indisponible_sans_base():
    """Sans persistance (base=None), la comparaison est indisponible."""
    moteur = MoteurSimilarite(None)
    assert moteur.est_disponible() is False


def test_indisponible_reference_vide(tmp_path):
    """Sur une base réelle mais SANS article de référence, la
    comparaison est indisponible (exigence 9.2)."""
    base, _ = ouvrir_base_temporaire(tmp_path)
    try:
        moteur = MoteurSimilarite(base)
        assert moteur.est_disponible() is False
    finally:
        base.fermer()


def test_indisponible_si_sklearn_absent(tmp_path, monkeypatch):
    """Si scikit-learn est absent, est_disponible() renvoie False
    même avec une référence non vide (exigence 9.1)."""
    base, _ = ouvrir_base_temporaire(tmp_path)
    try:
        base.ajouter_article_reference("Titre", "Contenu de reference", "real")
        # On simule l'absence de scikit-learn.
        monkeypatch.setattr(moteur_similarite, "SKLEARN_DISPONIBLE", False)
        moteur = MoteurSimilarite(base)
        assert moteur.est_disponible() is False
    finally:
        base.fermer()


# -------------------------------------------------------------
#  Cycle de vie du modèle : construction unique + cache (5.1, 5.2)
# -------------------------------------------------------------

@besoin_sklearn
def test_disponible_reference_non_vide(tmp_path):
    """Avec scikit-learn et une référence non vide, la comparaison
    est disponible."""
    base, _ = ouvrir_base_temporaire(tmp_path)
    try:
        base.ajouter_article_reference("Titre A", "Texte alpha beta", "fake")
        base.ajouter_article_reference("Titre B", "Texte gamma delta", "real")
        moteur = MoteurSimilarite(base)
        assert moteur.est_disponible() is True
    finally:
        base.fermer()


@besoin_sklearn
def test_modele_construit_une_seule_fois(tmp_path):
    """Le modèle TF-IDF est construit une fois puis réutilisé
    depuis le cache (exigences 5.1, 5.2)."""
    base, _ = ouvrir_base_temporaire(tmp_path)
    try:
        base.ajouter_article_reference("Titre A", "Texte alpha beta", "fake")
        moteur = MoteurSimilarite(base)

        # Premier appel : construction + mise en cache.
        moteur._construire_modele()
        assert moteur._modele_construit is True
        vectoriseur = moteur._vectoriseur
        matrice = moteur._matrice_reference

        # Second appel : aucune reconstruction (mêmes objets en cache).
        moteur._construire_modele()
        assert moteur._vectoriseur is vectoriseur
        assert moteur._matrice_reference is matrice
    finally:
        base.fermer()


@besoin_sklearn
def test_invalider_cache_force_reconstruction(tmp_path):
    """invalider_cache() vide le cache : la comparaison suivante
    reconstruit le modèle (exigence 5.4)."""
    base, _ = ouvrir_base_temporaire(tmp_path)
    try:
        base.ajouter_article_reference("Titre A", "Texte alpha beta", "fake")
        moteur = MoteurSimilarite(base)

        moteur._construire_modele()
        assert moteur._modele_construit is True

        moteur.invalider_cache()
        assert moteur._modele_construit is False
        assert moteur._vectoriseur is None
        assert moteur._matrice_reference is None
        assert moteur._articles_reference is None

        # Une nouvelle construction est alors possible.
        moteur._construire_modele()
        assert moteur._modele_construit is True
    finally:
        base.fermer()
