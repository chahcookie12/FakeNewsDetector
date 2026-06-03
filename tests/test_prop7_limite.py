# =============================================================
#  Test de propriété — Property 7 (task 3.5)
# =============================================================
#
#  Feature: database-persistence, Property 7: Limite de
#  l'historique — For any ensemble de N analyses enregistrées et
#  toute limite L, l'historique retourné contient exactement
#  min(L, N) analyses lorsque L >= 1, et contient les N analyses
#  lorsqu'aucune limite n'est fournie ; les analyses retournées
#  sont toujours les plus récentes selon l'ordre défini.
#
#  Validates: Requirements 4.5, 4.6

import uuid

from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from _db_helpers import ouvrir_base_temporaire, articles, resultats


# N analyses (non vide) à enregistrer.
_ensemble_analyses = st.lists(
    st.tuples(articles(), resultats()),
    min_size=1,
    max_size=12,
)


@settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    ensemble=_ensemble_analyses,
    # Limite valide (>= 1) couvrant des valeurs < N, = N et > N.
    limite=st.integers(min_value=1, max_value=20),
)
def test_limite_historique(tmp_path, ensemble, limite):
    base, _ = ouvrir_base_temporaire(tmp_path, nom=f"db_{uuid.uuid4().hex}.db")
    try:
        for article, resultat in ensemble:
            base.enregistrer_analyse(article, resultat)

        n = len(ensemble)

        # Référence : l'historique complet (sans limite) -> les N analyses.
        complet = base.recuperer_historique()
        assert len(complet) == n  # 4.6 : tout est retourné sans limite

        # Avec limite L >= 1 : exactement min(L, N).
        limite_resultat = base.recuperer_historique(limite=limite)
        assert len(limite_resultat) == min(limite, n)

        # Les analyses retournées sont les plus récentes selon l'ordre
        # défini : ce sont les min(L, N) premières de l'historique complet.
        ids_attendus = [ligne["id"] for ligne in complet[:min(limite, n)]]
        ids_obtenus = [ligne["id"] for ligne in limite_resultat]
        assert ids_obtenus == ids_attendus
    finally:
        base.fermer()
