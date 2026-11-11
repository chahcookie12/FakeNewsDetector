# =============================================================
#  Test de propriété — Property 1 : Étiquetage par fichier (task 2.2)
# =============================================================
#
#  Feature: news-similarity-detection, Property 1: Étiquetage par
#  fichier — Pour tout article importé, son étiquette est exactement
#  celle déduite de son fichier source (`Fake → fake`,
#  `real`/`True → real`) et appartient toujours à `{fake, real}`.
#
#  On vérifie ici la fonction `deduire_etiquette` du composant
#  ImportateurDataset :
#    - pour des variantes de casse des noms reconnus
#      (`Fake.csv`/`real.csv`/`True.csv`), l'étiquette déduite
#      appartient à `{fake, real}` et correspond au fichier ;
#    - pour des noms non reconnus, l'étiquette déduite est `None`.
#
#  Validates: Requirements 2.1, 2.2, 2.3

from hypothesis import given
from hypothesis import strategies as st

from classes.importateur_dataset import deduire_etiquette


# Étiquette attendue (canonique) pour chaque nom de fichier reconnu.
_NOMS_RECONNUS = {
    "Fake.csv": "fake",
    "real.csv": "real",
    "True.csv": "real",
}

# Ensemble des étiquettes valides.
_ETIQUETTES_VALIDES = {"fake", "real"}


def _variantes_de_casse(nom):
    """Construit une stratégie produisant des variantes de casse d'un nom.

    Pour chaque caractère alphabétique, on choisit aléatoirement
    minuscule ou majuscule ; les autres caractères (ex. le point)
    restent inchangés. Cela couvre `Fake.csv`, `FAKE.CSV`, `fAkE.csv`…
    """

    # Une stratégie booléenne par position alphabétique : True = majuscule.
    return st.tuples(
        *[st.booleans() for _ in nom]
    ).map(
        lambda bits: "".join(
            (c.upper() if maj else c.lower()) if c.isalpha() else c
            for c, maj in zip(nom, bits)
        )
    )


# Stratégie : un (nom_variant, etiquette_attendue) pour un nom reconnu.
_noms_reconnus_variants = st.sampled_from(list(_NOMS_RECONNUS.items())).flatmap(
    lambda paire: _variantes_de_casse(paire[0]).map(
        lambda variant: (variant, paire[1])
    )
)


@given(paire=_noms_reconnus_variants)
def test_etiquette_des_fichiers_reconnus(paire):
    """Toute variante de casse d'un nom reconnu déduit la bonne étiquette."""

    nom_variant, etiquette_attendue = paire
    etiquette = deduire_etiquette(nom_variant)

    # L'étiquette correspond exactement au fichier source.
    assert etiquette == etiquette_attendue, (
        f"{nom_variant!r} devrait donner {etiquette_attendue!r}, "
        f"obtenu {etiquette!r}"
    )

    # Et elle appartient strictement à l'ensemble { fake, real }.
    assert etiquette in _ETIQUETTES_VALIDES


# Stratégie : des noms quelconques, dont on exclut les noms reconnus
# (comparaison insensible à la casse) pour cibler le cas « non reconnu ».
_noms_non_reconnus = st.text(min_size=0, max_size=20).filter(
    lambda nom: nom.strip().lower() not in {
        n.lower() for n in _NOMS_RECONNUS
    }
)


@given(nom=_noms_non_reconnus)
def test_etiquette_des_fichiers_non_reconnus(nom):
    """Tout nom non reconnu ne déduit aucune étiquette (None)."""

    etiquette = deduire_etiquette(nom)
    assert etiquette is None, (
        f"{nom!r} ne devrait être associé à aucune étiquette, obtenu {etiquette!r}"
    )
