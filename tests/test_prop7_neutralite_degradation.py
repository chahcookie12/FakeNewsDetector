# =============================================================
#  Test de propriété — Property 7 (task 6.3)
# =============================================================
#
#  Feature: news-similarity-detection, Property 7 : Neutralité en
#  dégradation — Lorsque la similarité est indisponible (ajustement
#  nul), le score, le verdict ET le détail produits par
#  Score.calculer sont strictement identiques au calcul réalisé à
#  partir des seuls indicateurs de l'Analyseur (aucune ligne de
#  détail supplémentaire).
#
#  Validates: Requirements 9.3, 10.2

from hypothesis import given, settings
from hypothesis import strategies as st

from classes.score import Score


@st.composite
def indicateurs(draw):
    """Génère un dictionnaire d'indicateurs arbitraire, du même
    format que celui produit par Analyseur.analyser()."""
    nb_mots = draw(st.integers(min_value=0, max_value=300))
    # nb_mots_uniques ne peut pas dépasser nb_mots (cohérence), mais
    # la propriété tient même sans cette contrainte ; on la garde
    # réaliste tout de même.
    nb_mots_uniques = draw(st.integers(min_value=0, max_value=max(nb_mots, 0)))
    nb_suspects = draw(st.integers(min_value=0, max_value=20))
    mots_suspects = draw(
        st.lists(
            st.text(min_size=1, max_size=12),
            min_size=0,
            max_size=10,
        )
    )
    return {
        "sources_presentes": draw(st.booleans()),
        "nb_mots_suspects": nb_suspects,
        "mots_suspects": mots_suspects,
        "nb_mots": nb_mots,
        "nb_mots_uniques": nb_mots_uniques,
        "ratio_suspects": draw(
            st.floats(min_value=0.0, max_value=1.0, allow_nan=False)
        ),
    }


@settings(max_examples=10)
@given(
    ind=indicateurs(),
    etiquette=st.sampled_from(["fake", "real", None]),
    pourcentage=st.floats(min_value=0.0, max_value=100.0, allow_nan=False),
)
def test_neutralite_en_degradation(ind, etiquette, pourcentage):
    """Avec un ajustement de similarité nul (similarité
    indisponible), le résultat doit être identique au bit près au
    calcul à partir des seuls indicateurs — y compris le détail."""
    score = Score()

    # Référence : calcul à partir des seuls indicateurs (aucun
    # ajustement transmis), exactement comme avant l'ajout de la
    # couche de similarité.
    reference = score.calculer(ind)

    # Ajustement 0 explicite : doit être strictement identique.
    avec_zero = score.calculer(ind, ajustement_score=0)

    # Ajustement 0 + métadonnées de similarité fournies : la ligne
    # explicative ne doit PAS apparaître tant que l'ajustement reste
    # nul ; le résultat reste donc identique à la référence.
    avec_zero_et_metadonnees = score.calculer(
        ind,
        ajustement_score=0,
        etiquette_dominante=etiquette,
        meilleur_pourcentage=pourcentage,
    )

    assert avec_zero == reference
    assert avec_zero_et_metadonnees == reference

    # Vérification explicite des trois composantes (score, verdict,
    # detail) pour matérialiser l'exigence.
    assert avec_zero["score"] == reference["score"]
    assert avec_zero["verdict"] == reference["verdict"]
    assert avec_zero["detail"] == reference["detail"]

    assert avec_zero_et_metadonnees["score"] == reference["score"]
    assert avec_zero_et_metadonnees["verdict"] == reference["verdict"]
    assert avec_zero_et_metadonnees["detail"] == reference["detail"]
