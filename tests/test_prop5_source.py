# =============================================================
#  Test de propriété — Property 5 (task 5.3)
# =============================================================
#
#  Feature: database-persistence, Property 5: Normalisation de la
#  source absente — For any contenu inséré (analyse ou contenu
#  fiable), si la source fournie est nulle ou composée uniquement
#  d'espaces, la source stockée vaut Inconnue ; sinon la source
#  stockée est égale à la source fournie.
#
#  Validates: Requirements 2.7, 5.6

import uuid

from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from classes.article import Article
from _db_helpers import (
    ouvrir_base_temporaire,
    resultats,
    sources,
    caracteres_stockables,
)


def _source_attendue(source):
    """Réplique la règle de normalisation : None / vide / espaces
    -> "Inconnue" ; sinon la source est conservée telle quelle."""
    if source is None or str(source).strip() == "":
        return "Inconnue"
    return source


@settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    source=sources,
    resultat=resultats(),
    titre=st.text(caracteres_stockables, min_size=1, max_size=30),
    contenu=st.text(caracteres_stockables, min_size=1, max_size=80),
)
def test_normalisation_source_analyse_et_contenu_fiable(
    tmp_path, source, resultat, titre, contenu
):
    base, _ = ouvrir_base_temporaire(tmp_path, nom=f"db_{uuid.uuid4().hex}.db")
    try:
        attendue = _source_attendue(source)

        # --- Cas 1 : ANALYSE -------------------------------------
        # On insère une analyse avec la source testée, puis on lit la
        # source DIRECTEMENT dans la table "analyses" (requête SQL).
        article = Article(titre=titre, contenu=contenu, source=source)
        id_analyse = base.enregistrer_analyse(article, resultat)

        curseur = base.connexion.cursor()
        curseur.execute(
            "SELECT source FROM analyses WHERE id = ?", (id_analyse,)
        )
        source_analyse = curseur.fetchone()[0]
        assert source_analyse == attendue

        # --- Cas 2 : CONTENU FIABLE ------------------------------
        # On ajoute un contenu fiable avec la même source testée et on
        # lit sa source via recuperer_contenus_fiables().
        id_fiable = base.ajouter_contenu_fiable(titre, contenu, source)
        contenus = base.recuperer_contenus_fiables()
        ligne_fiable = next(c for c in contenus if c["id"] == id_fiable)
        assert ligne_fiable["source"] == attendue
    finally:
        base.fermer()
