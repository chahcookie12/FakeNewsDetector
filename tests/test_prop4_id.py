# =============================================================
#  Test de propriété — Property 4 (task 2.3)
# =============================================================
#
#  Feature: database-persistence, Property 4: Identifiant unique
#  et strictement positif — For any suite d'analyses enregistrées
#  avec succès, chaque enregistrement retourne un identifiant
#  entier strictement positif, et tous les identifiants retournés
#  sont distincts.
#
#  Validates: Requirements 2.6

import uuid

from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from _db_helpers import ouvrir_base_temporaire, articles, resultats


# Une suite (non vide) d'analyses : couples (Article, resultat).
_suite_analyses = st.lists(
    st.tuples(articles(), resultats()),
    min_size=1,
    max_size=12,
)


@settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(suite=_suite_analyses)
def test_id_unique_et_strictement_positif(tmp_path, suite):
    base, _ = ouvrir_base_temporaire(tmp_path, nom=f"db_{uuid.uuid4().hex}.db")
    try:
        ids = []
        for article, resultat in suite:
            id_cree = base.enregistrer_analyse(article, resultat)
            ids.append(id_cree)

        # Chaque identifiant retourné est un entier strictement positif.
        for id_cree in ids:
            assert isinstance(id_cree, int)
            assert id_cree > 0

        # Tous les identifiants retournés sont distincts.
        assert len(set(ids)) == len(ids)
    finally:
        base.fermer()
