# =============================================================
#  _db_helpers.py — utilitaires partagés par les tests
# =============================================================
#
#  Ce module REGROUPE :
#    - les stratégies Hypothesis pour générer des entrées valides
#      (articles, résultats de scoring, sources, dates) ;
#    - de petites fabriques pour construire un Article / un
#      resultat sans dépendre du moteur de scoring réel ;
#    - un utilitaire pour ouvrir une BaseDeDonnees sur un fichier
#      temporaire isolé.
#
#  Aucun effet de bord : chaque base est créée dans le tmp_path
#  fourni par pytest, ce qui rend les tests rapides et isolés.

import os
from datetime import datetime

from hypothesis import strategies as st

from classes.article import Article
from classes.base_donnees import BaseDeDonnees


# -------------------------------------------------------------
#  Ouverture d'une base temporaire isolée
# -------------------------------------------------------------
def ouvrir_base_temporaire(tmp_path, nom="fakenews.db"):
    """Ouvre une BaseDeDonnees dans un sous-dossier "data" du
    tmp_path fourni par pytest. Retourne (base, chemin)."""
    chemin = os.path.join(str(tmp_path), "data", nom)
    base = BaseDeDonnees(chemin=chemin)
    return base, chemin


# -------------------------------------------------------------
#  Verdicts valides (cohérents avec la classe Score)
# -------------------------------------------------------------
VERDICTS = ["FAKE", "DOUTEUX", "FIABLE"]


# -------------------------------------------------------------
#  Stratégies de base
# -------------------------------------------------------------

# Caractères "stockables" : tout l'Unicode SAUF les surrogates
# isolés (catégorie "Cs", ex. \ud800). Ces points de code sont des
# str Python valides mais ne sont PAS encodables en UTF-8, donc
# SQLite les rejette (UnicodeEncodeError). Ils n'apparaissent jamais
# dans un texte d'article réel (impossibles dans une source UTF-8
# valide), on les exclut donc des données générées.
caracteres_stockables = st.characters(blacklist_categories=["Cs"])

# Texte arbitraire SANS saut de ligne :
#   - le titre / contenu peuvent être unicode, espaces, longs ;
#   - on exclut "\n" et "\r" UNIQUEMENT pour les lignes de détail
#     (voir lignes_detail) car le détail est sérialisé par "\n".
texte_quelconque = st.text(caracteres_stockables, min_size=0, max_size=80)

# Titre / contenu : du texte non vide est plus réaliste, mais le
# schéma exige seulement NOT NULL (une chaîne vide reste valide).
titres = st.text(caracteres_stockables, min_size=1, max_size=60)
contenus = st.text(caracteres_stockables, min_size=1, max_size=200)

# Sources "présentes" : du texte qui contient au moins un
# caractère non-espace (sinon il serait normalisé en "Inconnue").
sources_presentes = st.text(caracteres_stockables, min_size=1, max_size=40).filter(
    lambda s: s.strip() != ""
)

# Sources "absentes" : None, chaîne vide, ou uniquement des espaces
# blancs (espaces, tabulations, sauts de ligne).
sources_absentes = st.one_of(
    st.none(),
    st.sampled_from(["", " ", "   ", "\t", "\n", " \t \n "]),
)

# Source quelconque : présente OU absente.
sources = st.one_of(sources_presentes, sources_absentes)

# Score entier 0..100.
scores = st.integers(min_value=0, max_value=100)

# Verdict parmi les trois étiquettes valides.
verdicts = st.sampled_from(VERDICTS)

# Une ligne de détail : du texte SANS saut de ligne (le détail est
# sérialisé en joignant les lignes par "\n", donc une ligne ne doit
# pas elle-même contenir "\n" ou "\r" pour un round-trip exact). On
# exclut aussi les surrogates isolés (catégorie "Cs"), non encodables
# en UTF-8 et donc rejetés par SQLite.
ligne_detail = st.text(
    alphabet=st.characters(blacklist_characters="\n\r", blacklist_categories=["Cs"]),
    min_size=0,
    max_size=40,
)

# Le détail : liste de lignes (éventuellement vide).
lignes_detail = st.lists(ligne_detail, min_size=0, max_size=8)

# Dates : datetime à la seconde près (microsecondes ignorées car le
# format de stockage "%Y-%m-%d %H:%M:%S" ne les conserve pas).
dates = st.datetimes(
    min_value=datetime(2000, 1, 1, 0, 0, 0),
    max_value=datetime(2035, 12, 31, 23, 59, 59),
).map(lambda d: d.replace(microsecond=0))


# -------------------------------------------------------------
#  Fabriques d'objets
# -------------------------------------------------------------

@st.composite
def articles(draw, source_strategy=sources):
    """Stratégie composite produisant un Article valide.

    Le paramètre source_strategy permet de restreindre la source
    (par ex. uniquement des sources présentes ou absentes)."""
    titre = draw(titres)
    contenu = draw(contenus)
    source = draw(source_strategy)
    date = draw(dates)
    return Article(titre=titre, contenu=contenu, source=source, date=date)


@st.composite
def resultats(draw):
    """Stratégie composite produisant un resultat de scoring
    {score, verdict, detail} structurellement valide."""
    return {
        "score": draw(scores),
        "verdict": draw(verdicts),
        "detail": draw(lignes_detail),
    }


def faire_article(titre="Titre", contenu="Contenu", source="source.fr",
                  date=None):
    """Fabrique simple (non-Hypothesis) d'un Article pour les
    tests par l'exemple."""
    if date is None:
        date = datetime(2024, 1, 1, 12, 0, 0)
    return Article(titre=titre, contenu=contenu, source=source, date=date)


def faire_resultat(score=50, verdict="DOUTEUX", detail=None):
    """Fabrique simple d'un resultat de scoring."""
    if detail is None:
        detail = ["Score de base : 50", "+0  aucune source détectée"]
    return {"score": score, "verdict": verdict, "detail": detail}
