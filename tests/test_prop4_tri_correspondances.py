# =============================================================
#  Test de propriété — Property 4 (task 4.6)
# =============================================================
#
#  Feature: news-similarity-detection, Property 4: Tri des
#  correspondances — Pour toute comparaison, la liste des
#  correspondances retournée par MoteurSimilarite.comparer est
#  triée par pourcentage DÉCROISSANT puis, à pourcentages égaux,
#  par titre alphabétique CROISSANT, de façon DÉTERMINISTE.
#
#  Validates: Requirements 6.2
#
#  --- Stratégie de test (sans scikit-learn) ---
#  comparer() s'appuie sur un calcul TF-IDF réel (scikit-learn),
#  dépendance OPTIONNELLE non installée ici. Pour exercer la pure
#  logique de SÉLECTION/TRI sans cette dépendance, on contourne
#  les deux seuls points de contact avec scikit-learn, exactement
#  comme test_moteur_resultat.test_comparer_tri_egalite_titre_croissant :
#    - est_disponible() est forcé à True (on saute la détection de
#      dépendance et la lecture de la base) ;
#    - _calculer_pourcentages() renvoie des pourcentages générés,
#      alignés avec une fausse _articles_reference.
#  La logique de tri (cœur de l'exigence 6.2) est ainsi testée
#  directement, sans mock du résultat lui-même.

from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from classes.article import Article
from classes.moteur_similarite import MoteurSimilarite


@st.composite
def _references_et_pourcentages(draw):
    """Génère une référence d'articles à TITRES DISTINCTS et une
    liste de pourcentages alignée.

    Les titres sont rendus distincts (pré-condition naturelle d'un
    départage déterministe par titre), et les pourcentages sont
    tirés dans un PETIT ensemble de valeurs pour forcer fréquemment
    des égalités, exerçant ainsi le départage secondaire par titre.
    """
    n = draw(st.integers(min_value=1, max_value=8))

    # Titres distincts : on tire un ensemble de bases puis on les
    # rend uniques par un suffixe d'index, garantissant l'unicité
    # tout en conservant une variété alphabétique.
    bases = draw(
        st.lists(
            st.text(
                alphabet="abcdefghijABCDEFGHIJ ",
                min_size=1,
                max_size=6,
            ),
            min_size=n,
            max_size=n,
        )
    )
    titres = [f"{base}#{i}" for i, base in enumerate(bases)]

    labels = draw(
        st.lists(st.sampled_from(["fake", "real"]), min_size=n, max_size=n)
    )

    # Petit ensemble de pourcentages -> nombreuses égalités.
    pourcentages = draw(
        st.lists(
            st.sampled_from([0.0, 25.0, 50.0, 50.0, 75.0, 100.0]),
            min_size=n,
            max_size=n,
        )
    )

    references = [
        {"titre": titre, "label": label}
        for titre, label in zip(titres, labels)
    ]
    return references, pourcentages


def _trier_par_logique_attendue(references, pourcentages):
    """Ordre de référence attendu : pourcentage décroissant, puis
    titre croissant à égalité ; tronqué à min(5, N)."""
    paires = [
        {"titre": r["titre"], "label": r["label"], "pourcentage": p}
        for r, p in zip(references, pourcentages)
    ]
    paires.sort(key=lambda c: (-c["pourcentage"], c["titre"]))
    return paires[: min(5, len(paires))]


@settings(
    max_examples=10,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(donnees=_references_et_pourcentages())
def test_tri_correspondances_decroissant_puis_titre_croissant(monkeypatch, donnees):
    references, pourcentages = donnees

    moteur = MoteurSimilarite(object())  # base factice, non utilisée

    # On court-circuite les deux points de contact avec scikit-learn.
    monkeypatch.setattr(moteur, "est_disponible", lambda: True)
    moteur._articles_reference = references
    monkeypatch.setattr(
        moteur, "_calculer_pourcentages", lambda article: list(pourcentages)
    )

    resultat = moteur.comparer(Article("x", "y", None))
    correspondances = resultat["correspondances"]

    # --- Propriété principale : tri pourcentage desc, titre asc ---
    for precedent, suivant in zip(correspondances, correspondances[1:]):
        # Pourcentage décroissant (jamais croissant entre voisins).
        assert precedent["pourcentage"] >= suivant["pourcentage"]
        # À pourcentages égaux : titre alphabétique croissant.
        if precedent["pourcentage"] == suivant["pourcentage"]:
            assert precedent["titre"] <= suivant["titre"]

    # L'ordre observé correspond exactement à l'ordre attendu.
    assert correspondances == _trier_par_logique_attendue(references, pourcentages)

    # --- Déterminisme : des appels répétés donnent le même ordre ---
    correspondances_bis = moteur.comparer(Article("x", "y", None))["correspondances"]
    assert correspondances_bis == correspondances
