# =============================================================
#  test_moteur_resultat.py
#  Tests unitaires — MoteurSimilarite : sélection, tri et
#  Resultat_Similarite (tâche 4.5)
# =============================================================
#
#  Ces tests couvrent UNIQUEMENT le périmètre de la tâche 4.5 :
#    - sélection des min(5, nombre de correspondances) meilleures
#      correspondances {titre, label, pourcentage} (exigence 6.1) ;
#    - tri par pourcentage décroissant puis titre croissant à
#      égalité, ordre déterministe (exigence 6.2) ;
#    - structure du Resultat_Similarite {disponible, correspondances,
#      ajustement_score} (exigence 6.3) ;
#    - correspondances vides sans erreur quand aucune n'est
#      pertinente (exigences 6.4, 9.5) ;
#    - indisponibilité (référence vide / scikit-learn absent) :
#      disponible=False, correspondances=[], ajustement_score=0.
#
#  Le calcul DIRECTIONNEL de l'ajustement (tâche 4.7) n'est PAS
#  testé ici : ajustement_score vaut 0 (placeholder neutre).
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
    """Ouvre une base temporaire alimentée d'articles de référence
    distincts (étiquettes variées)."""
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
    base.ajouter_article_reference(
        "Climat", "le rechauffement climatique et les emissions de carbone", "real"
    )
    base.ajouter_article_reference(
        "Sport", "le match de football et le championnat de la ligue", "fake"
    )
    base.ajouter_article_reference(
        "Sante", "les maladies graves et les traitements medicaux", "real"
    )
    return base


# -------------------------------------------------------------
#  Indisponibilité : résultat neutre (9.1 / 9.2)
# -------------------------------------------------------------

def test_comparer_indisponible_sans_base():
    """Sans persistance (base=None), comparer renvoie un résultat
    indisponible neutre."""
    moteur = MoteurSimilarite(None)
    resultat = moteur.comparer(Article("Titre", "un contenu", None))
    assert resultat == {
        "disponible": False,
        "correspondances": [],
        "ajustement_score": 0,
    }


def test_comparer_indisponible_reference_vide(tmp_path):
    """Sur une base sans article de référence, comparer renvoie un
    résultat indisponible neutre (exigence 9.2)."""
    base, _ = ouvrir_base_temporaire(tmp_path)
    try:
        moteur = MoteurSimilarite(base)
        resultat = moteur.comparer(Article("Titre", "un contenu", None))
        assert resultat["disponible"] is False
        assert resultat["correspondances"] == []
        assert resultat["ajustement_score"] == 0
    finally:
        base.fermer()


# -------------------------------------------------------------
#  Structure et sélection (exigences 6.1, 6.3)
# -------------------------------------------------------------

@besoin_sklearn
def test_comparer_structure_et_limite_a_cinq(tmp_path):
    """Le Resultat_Similarite a la bonne structure et au plus 5
    correspondances {titre, label, pourcentage} (exigences 6.1, 6.3)."""
    base = _base_avec_references(tmp_path)
    try:
        moteur = MoteurSimilarite(base)
        # Article proche de plusieurs références (vocabulaire commun)
        # pour obtenir de nombreuses correspondances non nulles.
        article = Article(
            "Actualite",
            "les maladies graves les marches financiers le championnat de football",
            None,
        )

        resultat = moteur.comparer(article)

        # Structure attendue.
        assert set(resultat.keys()) == {
            "disponible",
            "correspondances",
            "ajustement_score",
        }
        assert resultat["disponible"] is True
        assert resultat["ajustement_score"] == 0

        correspondances = resultat["correspondances"]
        # Au plus 5 entrées (min(5, N)).
        assert len(correspondances) <= 5
        # Chaque entrée a les bons champs et types/bornes.
        for c in correspondances:
            assert set(c.keys()) == {"titre", "label", "pourcentage"}
            assert c["label"] in {"fake", "real"}
            assert 0.0 <= c["pourcentage"] <= 100.0
    finally:
        base.fermer()


# -------------------------------------------------------------
#  Tri déterministe (exigence 6.2)
# -------------------------------------------------------------

@besoin_sklearn
def test_comparer_tri_pourcentage_decroissant(tmp_path):
    """Les correspondances sont triées par pourcentage décroissant."""
    base = _base_avec_references(tmp_path)
    try:
        moteur = MoteurSimilarite(base)
        article = Article(
            "Actualite",
            "les maladies graves et les marches financiers en hausse",
            None,
        )

        correspondances = moteur.comparer(article)["correspondances"]
        pourcentages = [c["pourcentage"] for c in correspondances]
        # Ordre décroissant.
        assert pourcentages == sorted(pourcentages, reverse=True)
    finally:
        base.fermer()


def test_comparer_tri_egalite_titre_croissant(tmp_path, monkeypatch):
    """À pourcentages égaux, l'ordre suit le titre alphabétique
    croissant, de façon déterministe (exigence 6.2)."""
    # On contourne le calcul TF-IDF pour contrôler exactement les
    # pourcentages : plusieurs valeurs identiques forcent le départage
    # par titre. Cela teste la logique de tri sans dépendre de sklearn.
    moteur = MoteurSimilarite(object())  # base factice non utilisée ici

    # est_disponible -> True pour atteindre la logique de sélection/tri.
    monkeypatch.setattr(moteur, "est_disponible", lambda: True)

    # Références alignées avec les pourcentages renvoyés ci-dessous.
    moteur._articles_reference = [
        {"titre": "Zeta", "label": "fake"},
        {"titre": "Alpha", "label": "real"},
        {"titre": "Mike", "label": "fake"},
        {"titre": "Bravo", "label": "real"},
    ]
    # Pourcentages : Zeta=80, Alpha=80, Mike=50, Bravo=80.
    monkeypatch.setattr(
        moteur, "_calculer_pourcentages", lambda article: [80.0, 80.0, 50.0, 80.0]
    )

    correspondances = moteur.comparer(Article("x", "y", None))["correspondances"]
    titres = [c["titre"] for c in correspondances]

    # À 80 % : Alpha, Bravo, Zeta (croissant) ; puis Mike (50 %).
    assert titres == ["Alpha", "Bravo", "Zeta", "Mike"]


# -------------------------------------------------------------
#  Aucune correspondance pertinente (exigences 6.4, 9.5)
# -------------------------------------------------------------

@besoin_sklearn
def test_comparer_aucune_correspondance_vecteur_nul(tmp_path):
    """Un article au texte hors vocabulaire produit un vecteur nul :
    correspondances vides, sans erreur, disponible=True (exigences
    6.4, 9.5)."""
    base = _base_avec_references(tmp_path)
    try:
        moteur = MoteurSimilarite(base)
        article = Article("zzzqqq", "xkcdfoo wibblewobble", None)

        resultat = moteur.comparer(article)
        assert resultat["disponible"] is True
        assert resultat["correspondances"] == []
        assert resultat["ajustement_score"] == 0
    finally:
        base.fermer()
