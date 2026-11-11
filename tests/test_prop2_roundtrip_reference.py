# =============================================================
#  Test de propriété — Property 2 (task 1.3)
# =============================================================
#
#  Feature: news-similarity-detection, Property 2: Round-trip de
#  la référence — Pour tout ensemble d'articles étiquetés
#  enregistrés via `ajouter_article_reference`, leur récupération
#  via `recuperer_articles_reference` restitue le titre, le
#  contenu et l'étiquette (label) enregistrés ; un import vide
#  produit une référence vide.
#
#  Validates: Requirements 4.4, 4.7, 4.8

import uuid

from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from _db_helpers import ouvrir_base_temporaire, sources_presentes, caracteres_stockables


# Étiquettes valides : strictement {fake, real} (cf. Requirement 4).
_labels = st.sampled_from(["fake", "real"])

# Un article de référence : (titre, contenu, label, source PRÉSENTE).
# On restreint la source aux sources présentes pour vérifier la
# CONSERVATION exacte ; la normalisation des sources absentes en
# "Inconnue" (Requirement 4.5) est couverte par le test unitaire dédié.
_article_reference = st.tuples(
    st.text(caracteres_stockables, min_size=1, max_size=40),    # titre
    st.text(caracteres_stockables, min_size=1, max_size=120),   # contenu
    _labels,                                                     # label
    sources_presentes,                                          # source non vide
).filter(
    # Titre et contenu doivent rester non vides APRÈS strip
    # (sinon l'enregistrement est rejeté — Requirement 4.3).
    lambda t: t[0].strip() != "" and t[1].strip() != ""
)

# Ensemble (éventuellement vide) d'articles de référence.
_ensemble_articles = st.lists(_article_reference, min_size=0, max_size=10)


# deadline=None : l'écriture SQLite sur fichier temporaire (Windows) peut
# dépasser le délai par défaut de 200 ms de Hypothesis sur certains
# exemples ; cette variabilité d'E/S ne reflète aucun problème de logique.
@settings(
    max_examples=10,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(articles=_ensemble_articles)
def test_round_trip_reference(tmp_path, articles):
    base, _ = ouvrir_base_temporaire(tmp_path, nom=f"db_{uuid.uuid4().hex}.db")
    try:
        # --- Enregistrement : on mémorise l'attendu indexé par id ---
        attendus_par_id = {}
        for titre, contenu, label, source in articles:
            id_cree = base.ajouter_article_reference(titre, contenu, label, source)
            # Identifiant entier strictement positif (Requirement 4.4).
            assert isinstance(id_cree, int) and id_cree > 0
            attendus_par_id[id_cree] = {
                "titre": titre,
                "contenu": contenu,
                "label": label,
            }

        recuperes = base.recuperer_articles_reference()

        # Un import vide produit une référence vide (Requirement 4.8).
        if not articles:
            assert recuperes == []
            return

        # Aucun article perdu ni ajouté.
        assert len(recuperes) == len(attendus_par_id)

        # Chaque article récupéré restitue titre, contenu et label
        # exactement tels qu'enregistrés (Requirements 4.4, 4.7).
        for ligne in recuperes:
            assert set(ligne.keys()) >= {"id", "titre", "contenu", "label"}
            attendu = attendus_par_id[ligne["id"]]
            assert ligne["titre"] == attendu["titre"]
            assert ligne["contenu"] == attendu["contenu"]
            assert ligne["label"] == attendu["label"]
            # Le label restitué appartient toujours à {fake, real}.
            assert ligne["label"] in ("fake", "real")
    finally:
        base.fermer()
