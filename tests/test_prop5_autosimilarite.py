# =============================================================
#  Test de propriété — Property 5 : Auto-similarité (task 4.4)
# =============================================================
#
#  Feature: news-similarity-detection, Property 5: Auto-similarité —
#  Pour tout article dont le texte comparable (après nettoyage) est
#  IDENTIQUE au contenu d'un Article_Reference, ce dernier figure
#  parmi les correspondances retournées par
#  `MoteurSimilarite.comparer`, avec un pourcentage de correspondance
#  supérieur ou égal à 99 %.
#
#  Validates: Requirements 5.6
#
#  NOTE D'ALIGNEMENT DU TEXTE COMPARABLE :
#  Le corpus de référence est construit à partir du SEUL champ
#  "contenu" de chaque Article_Reference. Or `_extraire_texte` combine
#  le titre et le contenu d'un Article entrant (titre + "\n" + contenu).
#  Pour reproduire fidèlement l'auto-similarité, l'article entrant est
#  donc construit avec un titre VIDE et un contenu ÉGAL au contenu
#  stocké de la référence choisie : son texte comparable est alors
#  exactement le contenu de référence (cf. test_moteur_comparaison.py).
#
#  DÉGRADATION GRACIEUSE : scikit-learn est une dépendance optionnelle.
#  En son absence, ce test est ignoré (skip) proprement.

import uuid

import pytest

from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from classes.article import Article
from classes.moteur_similarite import MoteurSimilarite, SKLEARN_DISPONIBLE

from _db_helpers import ouvrir_base_temporaire


# Skip conditionnel : sans scikit-learn, ce test de propriété est ignoré.
besoin_sklearn = pytest.mark.skipif(
    not SKLEARN_DISPONIBLE,
    reason="scikit-learn n'est pas installé (dépendance optionnelle)",
)


# -------------------------------------------------------------
#  Stratégies de génération
# -------------------------------------------------------------
#
#  On génère des contenus composés de VRAIS mots (lettres ASCII,
#  longueur >= 2) afin que le vocabulaire TF-IDF ne soit jamais vide
#  (le token_pattern par défaut de TfidfVectorizer ne retient que les
#  jetons alphanumériques d'au moins deux caractères). Cela garantit
#  qu'un contenu identique produit bien un vecteur non nul et donc une
#  auto-similarité mesurable.

# Un mot : au moins deux lettres minuscules (jeton TF-IDF valide).
_mot = st.text(
    alphabet=st.characters(min_codepoint=ord("a"), max_codepoint=ord("z")),
    min_size=2,
    max_size=8,
)

# Un texte : une suite de 1 à 8 mots séparés par des espaces. Non vide
# après strip (au moins un mot), donc accepté par la base et porteur
# d'au moins un terme du vocabulaire.
_texte_mots = st.lists(_mot, min_size=1, max_size=8).map(lambda mots: " ".join(mots))

# Un article de référence : (titre, contenu), tous deux à base de mots.
_article_reference = st.tuples(_texte_mots, _texte_mots)

# Un ensemble d'articles de référence DISTINCTS par leur contenu : on
# évite ainsi toute ambiguïté lors de la recherche de la référence
# identique (un seul contenu correspond exactement à l'article entrant).
_ensemble_references = st.lists(
    _article_reference,
    min_size=1,
    max_size=8,
    unique_by=lambda a: a[1],   # contenus distincts
)


@besoin_sklearn
@settings(
    max_examples=10,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(references=_ensemble_references, data=st.data())
def test_auto_similarite_figure_parmi_correspondances(tmp_path, references, data):
    """Un article identique (après nettoyage) à une référence figure
    parmi les correspondances avec un pourcentage >= 99 %."""
    base, _ = ouvrir_base_temporaire(tmp_path, nom=f"db_{uuid.uuid4().hex}.db")
    try:
        # --- Insertion des articles de référence ---
        for titre, contenu in references:
            base.ajouter_article_reference(titre, contenu, "real")

        # --- Choix d'une référence dont on reproduit le contenu ---
        # On tire un index parmi les références insérées ; son contenu
        # stocké servira de texte comparable identique pour l'entrant.
        index = data.draw(st.integers(min_value=0, max_value=len(references) - 1))
        titre_ref, contenu_ref = references[index]

        moteur = MoteurSimilarite(base)

        # Article entrant : titre VIDE pour que le texte comparable se
        # réduise au contenu, ÉGAL au contenu stocké de la référence.
        article = Article("", contenu_ref, None)

        resultat = moteur.comparer(article)

        # La comparaison est disponible (scikit-learn présent, référence
        # non vide) et produit au moins une correspondance.
        assert resultat["disponible"] is True
        assert len(resultat["correspondances"]) >= 1

        # Au moins une correspondance retournée atteint >= 99 % : c'est
        # la référence au contenu identique (Requirement 5.6). Comme la
        # correspondance identique obtient le pourcentage maximal (~100),
        # elle figure en tête et donc parmi les (au plus 5) meilleures.
        meilleur_pourcentage = max(
            c["pourcentage"] for c in resultat["correspondances"]
        )
        assert meilleur_pourcentage >= 99.0
    finally:
        base.fermer()
