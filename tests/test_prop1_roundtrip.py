# =============================================================
#  Test de propriété — Property 1 (task 3.2)
# =============================================================
#
#  Feature: database-persistence, Property 1: Round-trip de
#  persistance d'une analyse — For any ensemble d'analyses
#  (Article + résultat {score, verdict, detail}) enregistrées,
#  puis relues — y compris après fermeture et réouverture de la
#  base sur le même fichier — chaque analyse récupérée conserve le
#  titre, le score, le verdict et la date enregistrés, et aucune
#  ligne préexistante n'est perdue ni modifiée.
#
#  Validates: Requirements 1.6, 2.1, 2.2, 2.4, 4.2

import uuid

from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from classes.base_donnees import BaseDeDonnees
from _db_helpers import ouvrir_base_temporaire, articles, resultats


# Un ensemble (non vide) d'analyses à persister.
_ensemble_analyses = st.lists(
    st.tuples(articles(), resultats()),
    min_size=1,
    max_size=12,
)


@settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(ensemble=_ensemble_analyses)
def test_round_trip_persistance_analyse(tmp_path, ensemble):
    # Chemin de base unique par exemple : isolation totale entre
    # les itérations Hypothesis.
    chemin = None
    base, chemin = ouvrir_base_temporaire(tmp_path, nom=f"db_{uuid.uuid4().hex}.db")

    # --- Enregistrement : on mémorise ce qui a été soumis ---
    attendus_par_id = {}
    try:
        for article, resultat in ensemble:
            id_cree = base.enregistrer_analyse(article, resultat)
            attendus_par_id[id_cree] = {
                "titre": article.titre,
                "score": resultat["score"],
                "verdict": resultat["verdict"],
                "date": article.date.strftime("%Y-%m-%d %H:%M:%S"),
            }
    finally:
        # Fermeture pour forcer une relecture depuis le disque.
        base.fermer()

    # --- Réouverture du MÊME fichier puis relecture ---
    base2 = BaseDeDonnees(chemin=chemin)
    try:
        historique = base2.recuperer_historique()

        # Aucune ligne perdue : autant d'analyses relues qu'enregistrées.
        assert len(historique) == len(attendus_par_id)

        # Chaque analyse relue conserve titre, score, verdict, date.
        relus_par_id = {ligne["id"]: ligne for ligne in historique}
        assert set(relus_par_id.keys()) == set(attendus_par_id.keys())

        for id_analyse, attendu in attendus_par_id.items():
            relu = relus_par_id[id_analyse]
            assert relu["titre"] == attendu["titre"]
            assert relu["score"] == attendu["score"]
            assert relu["verdict"] == attendu["verdict"]
            assert relu["date"] == attendu["date"]
    finally:
        base2.fermer()
