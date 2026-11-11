# =============================================================
#  Tests d'intégration — Similarité (task 7.3)
# =============================================================
#
#  Feature: news-similarity-detection
#
#  Ces tests d'intégration vérifient le comportement BOUT EN BOUT
#  de la couche de similarité, sur une base SQLite TEMPORAIRE et
#  isolée (via ouvrir_base_temporaire) :
#
#    1. Import → comparaison : on écrit de vrais fichiers CSV
#       (Fake.csv / True.csv) dans un dossier dataset temporaire,
#       on lance ImportateurDataset(base).importer(dossier=...),
#       puis MoteurSimilarite(base).comparer(article) doit produire
#       un Resultat_Similarite valide (disponible=True, pourcentages
#       dans [0, 100]). Ce test est GARDÉ par scikit-learn : il est
#       ignoré (skip) si la dépendance optionnelle est absente.
#
#    2. Dégradation gracieuse : avec une référence VIDE (ou en
#       l'absence de scikit-learn), comparer() renvoie disponible=
#       False, correspondances=[], ajustement_score=0, ET le Score
#       reste calculable dans [0, 100] à partir des seuls indicateurs
#       de l'Analyseur (ajustement_score=0). Ce test s'exécute
#       TOUJOURS (aucun skip) : il prouve que le score demeure
#       calculable quand la similarité est indisponible.
#
#  Validates: Requirements 9.6, 10.3

import os

import pytest

from classes.analyseur import Analyseur
from classes.article import Article
from classes.importateur_dataset import ImportateurDataset
from classes.moteur_similarite import MoteurSimilarite, SKLEARN_DISPONIBLE
from classes.score import Score

from _db_helpers import ouvrir_base_temporaire


# -------------------------------------------------------------
#  Utilitaire : écrit un fichier CSV de référence minimal
# -------------------------------------------------------------
#  Le format suit le jeu ISOT : colonnes title, text, subject.
#  L'étiquette est déduite du NOM de fichier par l'importateur,
#  pas d'une colonne interne.

def _ecrire_csv(chemin, lignes):
    """Écrit un CSV (title,text,subject) à partir d'une liste de
    tuples (title, text, subject)."""
    contenu = ["title,text,subject"]
    for titre, texte, sujet in lignes:
        contenu.append(f"{titre},{texte},{sujet}")
    with open(chemin, "w", encoding="utf-8", newline="") as flux:
        flux.write("\n".join(contenu) + "\n")


# =============================================================
#  Test 1 : import → comparaison bout en bout
# =============================================================
#  GARDÉ par scikit-learn : la comparaison TF-IDF + cosinus dépend
#  de la dépendance optionnelle. Sans elle, ce flux n'est pas
#  applicable (la dégradation gracieuse est couverte par le test 2).
#
#  Validates: Requirements 9.6, 10.3

@pytest.mark.skipif(
    not SKLEARN_DISPONIBLE,
    reason="scikit-learn absent : la comparaison TF-IDF est indisponible.",
)
def test_import_puis_comparaison_bout_en_bout(tmp_path):
    # --- Base SQLite temporaire et isolée ---
    base, _ = ouvrir_base_temporaire(tmp_path)
    try:
        # --- Préparation d'un dossier dataset temporaire ---
        dossier = os.path.join(str(tmp_path), "dataset")
        os.makedirs(dossier, exist_ok=True)

        # Fake.csv -> étiquette "fake" ; True.csv -> étiquette "real".
        _ecrire_csv(
            os.path.join(dossier, "Fake.csv"),
            [
                ("Choc complot mondial", "Une revelation incroyable et secrete", "politics"),
                ("Alerte scandale urgent", "Un secret choquant jamais devoile", "news"),
            ],
        )
        _ecrire_csv(
            os.path.join(dossier, "True.csv"),
            [
                ("Rapport economique annuel", "La croissance progresse selon une etude", "economy"),
                ("Conference sur le climat", "Les chercheurs publient leurs resultats", "science"),
            ],
        )

        # --- Import bout en bout ---
        rapport = ImportateurDataset(base).importer(dossier=dossier)

        # 4 lignes valides importées (2 fake + 2 real).
        assert rapport["total_importes"] == 4
        assert rapport["importes"]["fake"] == 2
        assert rapport["importes"]["real"] == 2
        assert base.compter_articles_reference() == 4

        # --- Comparaison d'un article proche d'un article fake ---
        article = Article(
            titre="Choc complot mondial",
            contenu="Une revelation incroyable et secrete",
            source="test",
        )
        moteur = MoteurSimilarite(base)

        # La référence n'est pas vide et scikit-learn est présent.
        assert moteur.est_disponible() is True

        resultat = moteur.comparer(article)

        # Resultat_Similarite structurellement valide.
        assert resultat["disponible"] is True
        assert isinstance(resultat["correspondances"], list)
        # Au plus min(5, N) correspondances ; ici N = 4.
        assert 1 <= len(resultat["correspondances"]) <= 4

        # Chaque correspondance respecte le contrat (label + bornes).
        for corr in resultat["correspondances"]:
            assert corr["label"] in ("fake", "real")
            assert 0 <= corr["pourcentage"] <= 100

        # L'ajustement de score est borné comme attendu côté moteur.
        assert -20 <= resultat["ajustement_score"] <= 20

        # --- Le score reste calculable et valide après comparaison ---
        indicateurs = Analyseur().analyser(article)
        score = Score().calculer(
            indicateurs,
            ajustement_score=resultat["ajustement_score"],
        )
        assert 0 <= score["score"] <= 100
        assert score["verdict"] in ("FAKE", "DOUTEUX", "FIABLE")
    finally:
        base.fermer()


# =============================================================
#  Test 2 : dégradation gracieuse — référence vide / sans sklearn
# =============================================================
#  AUCUN skip : ce test doit s'exécuter en TOUTE circonstance,
#  y compris sans scikit-learn. Il prouve que le score reste
#  calculable lorsque la similarité est indisponible (Req 9.6, 10.3).
#
#  Validates: Requirements 9.6, 10.3

def test_degradation_gracieuse_score_reste_calculable(tmp_path):
    # --- Base temporaire SANS aucun article de référence ---
    base, _ = ouvrir_base_temporaire(tmp_path)
    try:
        # Référence vide : aucune ligne dans articles_reference.
        assert base.compter_articles_reference() == 0

        article = Article(
            titre="Un titre quelconque",
            contenu=(
                "Selon une etude publiee, les chercheurs analysent "
                "calmement les donnees disponibles sur le sujet."
            ),
            source="test",
        )

        moteur = MoteurSimilarite(base)

        # Référence vide (et/ou scikit-learn absent) : indisponible.
        assert moteur.est_disponible() is False

        resultat = moteur.comparer(article)

        # Resultat_Similarite neutre : disponible False, vide, 0.
        assert resultat["disponible"] is False
        assert resultat["correspondances"] == []
        assert resultat["ajustement_score"] == 0

        # --- Le score reste calculable à partir des seuls indicateurs ---
        indicateurs = Analyseur().analyser(article)
        score = Score().calculer(
            indicateurs,
            ajustement_score=resultat["ajustement_score"],  # 0
        )

        # Score valide dans [0, 100], verdict cohérent.
        assert 0 <= score["score"] <= 100
        assert score["verdict"] in ("FAKE", "DOUTEUX", "FIABLE")

        # Aucun ajustement appliqué : score identique à l'analyse
        # textuelle seule (sans argument d'ajustement).
        score_sans_similarite = Score().calculer(indicateurs)
        assert score["score"] == score_sans_similarite["score"]
        assert score["verdict"] == score_sans_similarite["verdict"]
        assert score["detail"] == score_sans_similarite["detail"]
    finally:
        base.fermer()
