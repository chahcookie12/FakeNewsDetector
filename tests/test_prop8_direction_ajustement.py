# =============================================================
#  Test de propriété — Property 8 : Direction de l'ajustement
#  (tâche 4.8)
# =============================================================
#
#  Feature: news-similarity-detection, Property 8 : Direction de
#  l'ajustement — Une forte similarité DOMINÉE par des articles
#  `fake` n'augmente jamais le score (ajustement ≤ 0), et une forte
#  similarité DOMINÉE par des articles `real` ne le diminue jamais
#  (ajustement ≥ 0).
#
#  Validates: Requirements 7.4, 7.5
#
#  PÉRIMÈTRE : on teste la méthode pure `_calculer_ajustement`, qui
#  reçoit directement une liste de correspondances {titre, label,
#  pourcentage} déjà sélectionnées/triées (pourcentage décroissant).
#  Cette logique directionnelle est indépendante de scikit-learn :
#  AUCUN skip n'est nécessaire (cf. tests/test_moteur_ajustement.py).
#
#  STRATÉGIE DE GÉNÉRATION (contrainte intelligente de l'espace) :
#  on génère des ensembles de correspondances où une étiquette est
#  STRICTEMENT MAJORITAIRE (dominante) et où la MEILLEURE
#  correspondance atteint au moins le seuil de 70 % (condition des
#  exigences 7.4 et 7.5). On vérifie alors le SIGNE de l'ajustement.

from hypothesis import given, settings
from hypothesis import strategies as st

from classes.moteur_similarite import MoteurSimilarite


SEUIL = MoteurSimilarite.SEUIL_AJUSTEMENT  # 70.0


def _moteur():
    """Moteur sans persistance : suffisant pour la méthode pure
    `_calculer_ajustement` (aucune dépendance scikit-learn)."""
    return MoteurSimilarite(None)


# Pourcentage de la MEILLEURE correspondance : au seuil ou au-dessus
# (≥ 70 %), borné à 100 — c'est la condition d'activation de
# l'ajustement directionnel.
_pourcentage_fort = st.floats(
    min_value=SEUIL, max_value=100.0, allow_nan=False, allow_infinity=False
)

# Pourcentages des autres correspondances : dans [0, meilleur], on les
# tire simplement dans [0, 100] puis on les borne au tri (la meilleure
# reste en tête).
_pourcentage_quelconque = st.floats(
    min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False
)


@st.composite
def _correspondances_dominees(draw):
    """Génère (liste_triée, label_dominant) : une liste NON VIDE de
    correspondances dont une étiquette est STRICTEMENT majoritaire et
    dont la meilleure correspondance atteint au moins 70 %.

    La liste est triée par pourcentage décroissant, comme le contrat
    d'entrée de `_calculer_ajustement` l'exige (la meilleure d'abord)."""
    dominant = draw(st.sampled_from(["fake", "real"]))
    autre = "real" if dominant == "fake" else "fake"

    # Majorité stricte : nb_dominant > nb_autre. On tire le nombre
    # d'étiquettes minoritaires (0..3) puis on garantit au moins une
    # de plus pour l'étiquette dominante.
    nb_autre = draw(st.integers(min_value=0, max_value=3))
    nb_dominant = draw(st.integers(min_value=nb_autre + 1, max_value=nb_autre + 4))

    labels = [dominant] * nb_dominant + [autre] * nb_autre

    # Pourcentages : la meilleure correspondance est forte (≥ 70 %),
    # les autres sont quelconques dans [0, 100].
    pourcentages = [draw(_pourcentage_fort)]
    for _ in range(len(labels) - 1):
        pourcentages.append(draw(_pourcentage_quelconque))

    # Apparie étiquettes et pourcentages, puis trie par pourcentage
    # décroissant (contrat : meilleure correspondance en tête). Le
    # tri ne change pas la composition majoritaire des étiquettes.
    correspondances = [
        {"titre": f"art{i}", "label": labels[i], "pourcentage": pourcentages[i]}
        for i in range(len(labels))
    ]
    correspondances.sort(key=lambda c: c["pourcentage"], reverse=True)
    return correspondances, dominant


@settings(max_examples=50)
@given(donnees=_correspondances_dominees())
def test_direction_ajustement_suit_etiquette_dominante(donnees):
    """Pour un ensemble de correspondances dont la meilleure atteint
    ≥ 70 % et dont une étiquette est strictement majoritaire :
      - majorité `fake`  -> ajustement ≤ 0 (n'augmente jamais) ;
      - majorité `real`  -> ajustement ≥ 0 (ne diminue jamais).

    **Validates: Requirements 7.4, 7.5**
    """
    correspondances, dominant = donnees
    ajustement = _moteur()._calculer_ajustement(correspondances)

    # L'ajustement reste borné à [-20, +20] (amplitude max du moteur).
    assert -MoteurSimilarite.AJUSTEMENT_MAX <= ajustement <= MoteurSimilarite.AJUSTEMENT_MAX

    if dominant == "fake":
        # Majorité fake : malus -> n'augmente jamais le score (7.4).
        assert ajustement <= 0
    else:
        # Majorité real : bonus -> ne diminue jamais le score (7.5).
        assert ajustement >= 0
