# =============================================================
#  Test de propriété — Property 3 (tâche 4.3)
# =============================================================
#
#  Feature: news-similarity-detection, Property 3 : Bornes de
#  similarité — Pour tout article comparé à une référence NON VIDE,
#  chaque pourcentage de correspondance est dans l'intervalle
#  fermé [0, 100].
#
#  Validates: Requirements 5.5
#
#  scikit-learn est une dépendance OPTIONNELLE (dégradation
#  gracieuse). Si elle est absente, ce test est ignoré (skip),
#  comme dans tests/test_moteur_comparaison.py et
#  tests/test_moteur_resultat.py.

import uuid

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from classes.article import Article
from classes.moteur_similarite import MoteurSimilarite, SKLEARN_DISPONIBLE

from _db_helpers import ouvrir_base_temporaire


# Skip conditionnel : sans scikit-learn, la comparaison par
# similarité est indisponible, on ignore donc ce test.
besoin_sklearn = pytest.mark.skipif(
    not SKLEARN_DISPONIBLE,
    reason="scikit-learn n'est pas installé (dépendance optionnelle)",
)


# -------------------------------------------------------------
#  Générateurs : on produit des textes RÉELLEMENT lexicaux
# -------------------------------------------------------------
#  TF-IDF a besoin d'un vocabulaire non vide pour ajuster son
#  vectoriseur : on tire donc les contenus dans un petit lexique de
#  mots, ce qui garantit que la référence produit un vocabulaire
#  exploitable (pas d'erreur "empty vocabulary") et que la
#  comparaison est réellement exercée. C'est une contrainte
#  intelligente de l'espace d'entrée (mots plutôt qu'Unicode brut).
_lexique = st.sampled_from(
    [
        "vaccin", "terre", "plate", "complot", "bourse", "marche",
        "sante", "maladie", "science", "economie", "politique",
        "climat", "energie", "donnee", "article", "presse",
    ]
)

# Un texte = une suite non vide de mots séparés par des espaces.
_texte_mots = st.lists(_lexique, min_size=1, max_size=8).map(" ".join)

# Étiquette appartenant strictement à l'ensemble {fake, real}.
_labels = st.sampled_from(["fake", "real"])


@st.composite
def _references_non_vides(draw):
    """Liste NON VIDE de tuples (titre, contenu, label) à insérer
    comme articles de référence."""
    n = draw(st.integers(min_value=1, max_value=6))
    refs = []
    for _ in range(n):
        titre = draw(_texte_mots)
        contenu = draw(_texte_mots)
        label = draw(_labels)
        refs.append((titre, contenu, label))
    return refs


@besoin_sklearn
@settings(
    max_examples=10,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(references=_references_non_vides(), titre=_texte_mots, contenu=_texte_mots)
def test_bornes_pourcentages_dans_zero_cent(tmp_path, references, titre, contenu):
    """Pour une référence non vide et un article entrant, chaque
    pourcentage de correspondance retourné par comparer() est dans
    l'intervalle fermé [0, 100].

    **Validates: Requirements 5.5**
    """
    base, _ = ouvrir_base_temporaire(tmp_path, nom=f"db_{uuid.uuid4().hex}.db")
    try:
        # Alimente une référence NON VIDE.
        for ref_titre, ref_contenu, ref_label in references:
            base.ajouter_article_reference(ref_titre, ref_contenu, ref_label)

        moteur = MoteurSimilarite(base)
        article = Article(titre=titre, contenu=contenu, source=None)

        resultat = moteur.comparer(article)

        # Chaque pourcentage de correspondance est borné dans [0, 100].
        for correspondance in resultat["correspondances"]:
            pourcentage = correspondance["pourcentage"]
            assert 0 <= pourcentage <= 100
    finally:
        base.fermer()
