# =============================================================
#  Test de propriété — Property 2 (task 2.2)
# =============================================================
#
#  Feature: database-persistence, Property 2: Round-trip de
#  sérialisation du détail — For any liste de lignes de détail
#  produite pour une analyse, la sérialisation en texte puis la
#  désérialisation préservent l'intégralité des lignes dans le
#  même ordre.
#
#  Validates: Requirements 2.2
#
#  On vérifie : _deserialiser_detail(_serialiser_detail(lignes)) == lignes
#  (intégralité ET ordre conservés).
#
#  Note sur le domaine d'entrée : le détail réel est produit par
#  la classe Score et se compose toujours de lignes NON VIDES et
#  SANS saut de ligne (ex. "Score de base : 50"). On contraint donc
#  intelligemment le générateur à cet espace d'entrée : des lignes
#  non vides dépourvues de "\n"/"\r" (séparateur de sérialisation).
#  La liste elle-même peut être vide (détail absent).

import uuid

from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from _db_helpers import ouvrir_base_temporaire, caracteres_stockables


# Une ligne de détail réaliste : non vide, sans séparateur "\n"/"\r"
# ni surrogate isolé (non encodable UTF-8, rejeté par SQLite).
_ligne = st.text(
    alphabet=st.characters(blacklist_characters="\n\r", blacklist_categories=["Cs"]),
    min_size=1,
    max_size=40,
)

# Le détail : liste de lignes (éventuellement vide).
_lignes_detail = st.lists(_ligne, min_size=0, max_size=8)


@settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(lignes=_lignes_detail)
def test_round_trip_serialisation_detail(tmp_path, lignes):
    base, _ = ouvrir_base_temporaire(tmp_path, nom=f"db_{uuid.uuid4().hex}.db")
    try:
        texte = base._serialiser_detail(lignes)
        # Le texte sérialisé doit être une chaîne (stockable en TEXT).
        assert isinstance(texte, str)

        # Round-trip : on retrouve EXACTEMENT la liste d'origine,
        # avec toutes ses lignes et dans le même ordre.
        assert base._deserialiser_detail(texte) == lignes
    finally:
        base.fermer()
