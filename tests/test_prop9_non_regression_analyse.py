# =============================================================
#  Test de propriété — Property 9 (task 6.4)
# =============================================================
#
#  Feature: news-similarity-detection, Property 9 : Non-régression
#  de l'analyse — La présence du moteur de similarité ne modifie
#  pas les indicateurs produits par l'Analyseur.
#
#  Concrètement : pour un même article, les indicateurs renvoyés
#  par Analyseur.analyser(article) doivent rester STRICTEMENT
#  identiques avant et après un appel à MoteurSimilarite.comparer(
#  article). Le moteur ne reçoit jamais le dictionnaire
#  d'indicateurs et ne doit donc en muter aucune valeur.
#
#  On exerce la propriété sur le chemin de DÉGRADATION GRACIEUSE
#  (base de référence à None) : est_disponible() renvoie False,
#  comparer() prend la voie neutre, et l'analyse classique doit
#  rester intacte. Cela rend le test indépendant de la présence
#  de scikit-learn.
#
#  Validates: Requirements 10.1

import copy

from hypothesis import given, settings
from hypothesis import strategies as st

from classes.article import Article
from classes.analyseur import Analyseur
from classes.moteur_similarite import MoteurSimilarite


# Générateur de texte basé sur des MOTS : on assemble des mots
# alphabétiques (éventuellement des mots "suspects" pour exercer les
# indicateurs correspondants) séparés par des espaces. Cela produit
# un contenu réaliste pour l'Analyseur tout en restant simple.
_mots = st.one_of(
    st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz",
        min_size=1,
        max_size=10,
    ),
    st.sampled_from(
        ["urgent", "choc", "incroyable", "scandale", "complot", "vaccin"]
    ),
)

_textes = st.builds(
    lambda mots: " ".join(mots),
    st.lists(_mots, min_size=0, max_size=30),
)


@settings(max_examples=10, deadline=None)
@given(titre=_textes, contenu=_textes)
def test_comparer_ne_modifie_pas_les_indicateurs(titre, contenu):
    """Property 9 : comparer() ne mute pas les indicateurs de l'Analyseur.

    Validates: Requirements 10.1
    """
    article = Article(titre=titre, contenu=contenu, source="test")

    analyseur = Analyseur()

    # Indicateurs de référence, calculés AVANT toute comparaison.
    indicateurs_avant = analyseur.analyser(article)

    # Copie profonde indépendante servant de témoin : aucune
    # référence partagée avec le dictionnaire ci-dessus.
    temoin = copy.deepcopy(indicateurs_avant)

    # Appel au moteur de similarité sur le MÊME article. base=None
    # déclenche la dégradation gracieuse : la comparaison est
    # indisponible mais ne doit toucher à rien de l'analyse.
    moteur = MoteurSimilarite(base=None)
    resultat = moteur.comparer(article)

    # Le résultat de similarité est bien neutre (dégradation), mais
    # surtout il n'a modifié aucun indicateur de l'Analyseur.
    assert resultat["disponible"] is False
    assert resultat["ajustement_score"] == 0

    # Les indicateurs déjà calculés sont inchangés (objet en place).
    assert indicateurs_avant == temoin

    # Et une nouvelle analyse du même article redonne exactement les
    # mêmes indicateurs : la présence du moteur n'a rien altéré.
    indicateurs_apres = analyseur.analyser(article)
    assert indicateurs_apres == temoin
