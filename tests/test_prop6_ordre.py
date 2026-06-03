# =============================================================
#  Test de propriété — Property 6 (task 3.4)
# =============================================================
#
#  Feature: database-persistence, Property 6: Ordre de
#  l'historique — For any ensemble d'analyses enregistrées (dates
#  éventuellement identiques), l'historique retourné est trié par
#  date décroissante, et à dates égales par identifiant décroissant.
#
#  Validates: Requirements 4.1

import uuid
from datetime import datetime, timedelta

from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from classes.article import Article
from _db_helpers import ouvrir_base_temporaire, resultats, caracteres_stockables


# Pour FORCER l'apparition de dates identiques (sinon des dates
# purement aléatoires se répètent rarement), on tire les dates dans
# un PETIT ensemble de dates candidates. Ainsi le départage par id
# décroissant est réellement exercé.
_dates_candidates = st.builds(
    lambda jours, secondes: datetime(2020, 1, 1, 0, 0, 0)
    + timedelta(days=jours, seconds=secondes),
    st.integers(min_value=0, max_value=3),
    st.sampled_from([0, 1, 2]),
)


@st.composite
def _analyses_dates_repetees(draw):
    """Liste (non vide) de couples (Article, resultat) dont les
    dates sont tirées d'un petit ensemble, garantissant des dates
    identiques fréquentes."""
    n = draw(st.integers(min_value=1, max_value=12))
    couples = []
    for _ in range(n):
        date = draw(_dates_candidates)
        article = Article(
            titre=draw(st.text(caracteres_stockables, min_size=1, max_size=20)),
            contenu=draw(st.text(caracteres_stockables, min_size=1, max_size=40)),
            source=draw(st.text(caracteres_stockables, min_size=0, max_size=10)),
            date=date,
        )
        couples.append((article, draw(resultats())))
    return couples


@settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(ensemble=_analyses_dates_repetees())
def test_ordre_historique_date_desc_puis_id_desc(tmp_path, ensemble):
    base, _ = ouvrir_base_temporaire(tmp_path, nom=f"db_{uuid.uuid4().hex}.db")
    try:
        for article, resultat in ensemble:
            base.enregistrer_analyse(article, resultat)

        historique = base.recuperer_historique()

        # Couple (date, id) pour chaque analyse relue.
        observe = [(ligne["date"], ligne["id"]) for ligne in historique]

        # L'ordre attendu : date DESC, puis id DESC à dates égales.
        # On trie une COPIE selon ce critère et on compare.
        attendu = sorted(observe, key=lambda t: (t[0], t[1]), reverse=True)

        assert observe == attendu
    finally:
        base.fermer()
