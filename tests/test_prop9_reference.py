# =============================================================
#  Test de propriété — Property 9 (task 5.2)
# =============================================================
#
#  Feature: database-persistence, Property 9: Round-trip de la
#  base de référence — For any ensemble de contenus fiables
#  ajoutés, leur récupération retourne pour chacun un identifiant,
#  le titre, le contenu et la source enregistrés ; lorsqu'aucun
#  contenu n'a été ajouté, la récupération retourne une collection
#  vide.
#
#  Validates: Requirements 5.1, 5.2, 5.5, 5.7

import uuid

from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from _db_helpers import ouvrir_base_temporaire, sources_presentes, caracteres_stockables


# Un contenu fiable : (titre, contenu, source PRÉSENTE).
# On restreint la source aux sources présentes pour vérifier la
# CONSERVATION exacte (la normalisation des sources absentes est
# couverte par la Property 5, test dédié).
_contenu_fiable = st.tuples(
    st.text(caracteres_stockables, min_size=1, max_size=40),    # titre
    st.text(caracteres_stockables, min_size=1, max_size=120),   # contenu
    sources_presentes,                   # source non vide
)

# Ensemble (éventuellement vide) de contenus fiables.
_ensemble_contenus = st.lists(_contenu_fiable, min_size=0, max_size=10)


@settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(contenus=_ensemble_contenus)
def test_round_trip_base_reference(tmp_path, contenus):
    base, _ = ouvrir_base_temporaire(tmp_path, nom=f"db_{uuid.uuid4().hex}.db")
    try:
        # --- Ajout : on mémorise l'attendu indexé par id retourné ---
        attendus_par_id = {}
        for titre, contenu, source in contenus:
            id_cree = base.ajouter_contenu_fiable(titre, contenu, source)
            assert isinstance(id_cree, int) and id_cree > 0
            attendus_par_id[id_cree] = {
                "titre": titre,
                "contenu": contenu,
                "source": source,
            }

        recuperes = base.recuperer_contenus_fiables()

        # Collection vide si aucun contenu n'a été ajouté (5.5).
        if not contenus:
            assert recuperes == []
            return

        # Aucun contenu perdu ni ajouté.
        assert len(recuperes) == len(attendus_par_id)

        # Chaque contenu récupéré comporte id, titre, contenu, source
        # et correspond exactement à ce qui a été ajouté (5.1, 5.2, 5.7).
        for ligne in recuperes:
            assert set(ligne.keys()) >= {"id", "titre", "contenu", "source"}
            attendu = attendus_par_id[ligne["id"]]
            assert ligne["titre"] == attendu["titre"]
            assert ligne["contenu"] == attendu["contenu"]
            assert ligne["source"] == attendu["source"]
    finally:
        base.fermer()
