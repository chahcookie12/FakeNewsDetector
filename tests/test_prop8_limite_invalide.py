# =============================================================
#  Test de propriété — Property 8 (task 3.6)
# =============================================================
#
#  Feature: database-persistence, Property 8: Erreur sur limite
#  invalide — For any limite strictement inférieure à 1, la
#  récupération de l'historique signale une erreur et ne retourne
#  aucune analyse.
#
#  Validates: Requirements 4.7

import uuid

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from classes.base_donnees import ErreurBaseDeDonnees
from _db_helpers import ouvrir_base_temporaire, articles, resultats


# Petit ensemble d'analyses préexistantes : la propriété doit tenir
# que la base soit vide ou non. On en met quelques-unes pour prouver
# qu'AUCUNE n'est retournée malgré leur présence.
_ensemble_analyses = st.lists(
    st.tuples(articles(), resultats()),
    min_size=0,
    max_size=6,
)

# Toute limite strictement inférieure à 1 (zéro et négatifs).
_limites_invalides = st.integers(max_value=0)


@settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(ensemble=_ensemble_analyses, limite=_limites_invalides)
def test_limite_invalide_signale_erreur(tmp_path, ensemble, limite):
    base, _ = ouvrir_base_temporaire(tmp_path, nom=f"db_{uuid.uuid4().hex}.db")
    try:
        for article, resultat in ensemble:
            base.enregistrer_analyse(article, resultat)

        # Une limite < 1 signale une erreur métier et ne retourne rien
        # (l'exception interrompt l'appel : aucune analyse n'est rendue).
        with pytest.raises(ErreurBaseDeDonnees):
            base.recuperer_historique(limite=limite)
    finally:
        base.fermer()
