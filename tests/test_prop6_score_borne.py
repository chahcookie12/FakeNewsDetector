# =============================================================
#  Test de propriété — Property 6 : Score borné (task 6.2)
# =============================================================
#
#  Feature: news-similarity-detection, Property 6: Score borné —
#  Pour tout ensemble d'indicateurs et tout ajustement de
#  similarité, le score final reste dans [0, 100] et le verdict
#  reste cohérent avec les seuils FAKE/DOUTEUX/FIABLE.
#
#  La classe Score est PURE (aucune dépendance à scikit-learn) :
#  on peut donc générer des indicateurs arbitraires et un
#  ajustement arbitraire, puis vérifier les invariants de sortie.
#
#  On tire l'ajustement dans un intervalle large (-100..100) pour
#  exercer le clamp interne [-20, +20] (méthode _borner_ajustement)
#  ET le clamp final [0, 100] du score.
#
#  Validates: Requirements 7.2, 7.3

from hypothesis import given, settings
from hypothesis import strategies as st

from classes.score import Score


# -------------------------------------------------------------
#  Stratégie : un dictionnaire d'indicateurs arbitraire mais
#  structurellement valide (mêmes clés que Analyseur.analyser()).
# -------------------------------------------------------------
@st.composite
def indicateurs(draw):
    nb_mots = draw(st.integers(min_value=0, max_value=500))
    nb_mots_uniques = draw(st.integers(min_value=0, max_value=500))
    nb_mots_suspects = draw(st.integers(min_value=0, max_value=50))
    # Liste de mots suspects cohérente en longueur avec le compteur.
    mots_suspects = draw(
        st.lists(
            st.text(min_size=1, max_size=10),
            min_size=nb_mots_suspects,
            max_size=nb_mots_suspects,
        )
    )
    ratio_suspects = draw(
        st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
    )
    return {
        "sources_presentes": draw(st.booleans()),
        "nb_mots_suspects": nb_mots_suspects,
        "mots_suspects": mots_suspects,
        "nb_mots": nb_mots,
        "nb_mots_uniques": nb_mots_uniques,
        "ratio_suspects": ratio_suspects,
    }


@settings(max_examples=10)
@given(
    ind=indicateurs(),
    ajustement=st.integers(min_value=-100, max_value=100),
)
def test_score_borne_et_verdict_coherent(ind, ajustement):
    """Validates: Requirements 7.2, 7.3

    Pour tout indicateur et tout ajustement, le score reste dans
    [0, 100] et le verdict respecte exactement les seuils."""
    score = Score()
    resultat = score.calculer(ind, ajustement_score=ajustement)

    valeur = resultat["score"]
    verdict = resultat["verdict"]

    # Exigence 7.2 : le score final est borné à [0, 100].
    assert 0 <= valeur <= 100

    # Exigence 7.3 : le verdict est cohérent avec les seuils.
    if valeur < Score.SEUIL_FAKE:          # < 40
        attendu = "FAKE"
    elif valeur < Score.SEUIL_DOUTEUX:     # 40 <= score < 70
        attendu = "DOUTEUX"
    else:                                  # >= 70
        attendu = "FIABLE"

    assert verdict == attendu
