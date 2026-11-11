# =============================================================
#  Tests unitaires — Import du jeu de référence (task 2.4)
# =============================================================
#
#  Feature : news-similarity-detection — composant ImportateurDataset.
#
#  Ces tests par l'exemple couvrent l'import par lot complet via
#  ImportateurDataset.importer(dossier=...). Ils vérifient :
#    - le mapping souple des colonnes (title/titre, text/contenu avec
#      priorité, subject manquant -> "Inconnue") ;
#    - l'ignorance des lignes vides / inexploitables, comptées dans
#      lignes_ignorees ;
#    - la justesse du rapport de comptage (importes par étiquette,
#      total, fichiers ignorés) ;
#    - le cas du dossier introuvable (aucun import).
#
#  Validates: Requirements 1.6, 1.7, 3.1, 3.2, 3.4, 3.5

import os
import csv

from classes.importateur_dataset import ImportateurDataset
from _db_helpers import ouvrir_base_temporaire


# -------------------------------------------------------------
#  Utilitaires de test
# -------------------------------------------------------------

def _ecrire_csv(dossier, nom, entetes, lignes):
    """Écrit un fichier CSV `nom` dans `dossier` avec les `entetes`
    fournis et les `lignes` (liste de listes de valeurs)."""
    os.makedirs(dossier, exist_ok=True)
    chemin = os.path.join(dossier, nom)
    with open(chemin, "w", encoding="utf-8", newline="") as flux:
        ecrivain = csv.writer(flux)
        ecrivain.writerow(entetes)
        for ligne in lignes:
            ecrivain.writerow(ligne)
    return chemin


def _index_par_titre(articles):
    """Indexe une liste d'articles de référence par leur titre."""
    return {a["titre"]: a for a in articles}


# -------------------------------------------------------------
#  Mapping souple : title/titre, text/contenu (priorité), subject
# -------------------------------------------------------------

def test_mapping_souple_colonnes_standard(tmp_path):
    """Colonnes title/text/subject : titre, contenu combiné et source
    sont correctement extraits (Req 3.1, 3.2, 3.3)."""
    base, _ = ouvrir_base_temporaire(tmp_path)
    dossier = os.path.join(str(tmp_path), "dataset")
    _ecrire_csv(
        dossier, "Fake.csv",
        ["title", "text", "subject"],
        [["Titre A", "Corps A", "politique"]],
    )

    rapport = ImportateurDataset(base).importer(dossier=dossier)

    articles = base.recuperer_articles_reference()
    assert len(articles) == 1
    article = articles[0]
    assert article["titre"] == "Titre A"
    # Contenu = titre puis texte, séparés par un saut de ligne (Req 1.2).
    assert article["contenu"] == "Titre A\nCorps A"
    assert article["label"] == "fake"
    assert article["source"] == "politique"
    assert rapport["importes"]["fake"] == 1


def test_mapping_souple_variantes_titre_contenu(tmp_path):
    """Les variantes francophones titre/contenu sont reconnues, casse et
    espaces tolérés (Req 3.1, 3.2)."""
    base, _ = ouvrir_base_temporaire(tmp_path)
    dossier = os.path.join(str(tmp_path), "dataset")
    _ecrire_csv(
        dossier, "real.csv",
        [" Titre ", "CONTENU", "subject"],
        [["Mon titre", "Mon contenu", "monde"]],
    )

    ImportateurDataset(base).importer(dossier=dossier)

    articles = base.recuperer_articles_reference()
    assert len(articles) == 1
    assert articles[0]["titre"] == "Mon titre"
    assert articles[0]["contenu"] == "Mon titre\nMon contenu"
    assert articles[0]["label"] == "real"


def test_priorite_title_sur_titre_et_text_sur_contenu(tmp_path):
    """Quand title et titre (resp. text et contenu) coexistent, ce sont
    title et text qui priment (Req 3.1, 3.2)."""
    base, _ = ouvrir_base_temporaire(tmp_path)
    dossier = os.path.join(str(tmp_path), "dataset")
    _ecrire_csv(
        dossier, "Fake.csv",
        ["title", "titre", "text", "contenu"],
        [["Titre prioritaire", "Titre secondaire",
          "Texte prioritaire", "Contenu secondaire"]],
    )

    ImportateurDataset(base).importer(dossier=dossier)

    articles = base.recuperer_articles_reference()
    assert len(articles) == 1
    assert articles[0]["titre"] == "Titre prioritaire"
    assert articles[0]["contenu"] == "Titre prioritaire\nTexte prioritaire"


def test_subject_manquant_donne_source_inconnue(tmp_path):
    """Sans colonne subject, la source vaut "Inconnue" (Req 3.4)."""
    base, _ = ouvrir_base_temporaire(tmp_path)
    dossier = os.path.join(str(tmp_path), "dataset")
    _ecrire_csv(
        dossier, "Fake.csv",
        ["title", "text"],
        [["Titre sans sujet", "Corps sans sujet"]],
    )

    ImportateurDataset(base).importer(dossier=dossier)

    articles = base.recuperer_articles_reference()
    assert len(articles) == 1
    assert articles[0]["source"] == "Inconnue"


def test_subject_vide_donne_source_inconnue(tmp_path):
    """Colonne subject présente mais vide après strip -> "Inconnue"
    (Req 3.4)."""
    base, _ = ouvrir_base_temporaire(tmp_path)
    dossier = os.path.join(str(tmp_path), "dataset")
    _ecrire_csv(
        dossier, "Fake.csv",
        ["title", "text", "subject"],
        [["Titre", "Corps", "   "]],
    )

    ImportateurDataset(base).importer(dossier=dossier)

    articles = base.recuperer_articles_reference()
    assert len(articles) == 1
    assert articles[0]["source"] == "Inconnue"


# -------------------------------------------------------------
#  Lignes vides / inexploitables ignorées (Req 3.5)
# -------------------------------------------------------------

def test_lignes_vides_ignorees_et_comptees(tmp_path):
    """Les lignes sans titre ni contenu exploitables sont ignorées et
    comptées dans lignes_ignorees, l'import des autres se poursuit
    (Req 3.5)."""
    base, _ = ouvrir_base_temporaire(tmp_path)
    dossier = os.path.join(str(tmp_path), "dataset")
    _ecrire_csv(
        dossier, "Fake.csv",
        ["title", "text", "subject"],
        [
            ["Bon titre", "Bon corps", "sujet"],   # importée
            ["", "", "sujet"],                        # vide -> ignorée
            ["   ", "   ", "sujet"],                  # espaces -> ignorée
            ["Autre titre", "Autre corps", "sujet"],  # importée
        ],
    )

    rapport = ImportateurDataset(base).importer(dossier=dossier)

    assert rapport["lignes_ignorees"] == 2
    assert rapport["total_importes"] == 2
    assert rapport["importes"]["fake"] == 2
    assert base.compter_articles_reference() == 2


def test_ligne_avec_contenu_seul_est_importee(tmp_path):
    """Une ligne sans titre mais avec un contenu reste exploitable : le
    contenu sert de titre de secours (Req 3.5, contrainte titre non
    vide)."""
    base, _ = ouvrir_base_temporaire(tmp_path)
    dossier = os.path.join(str(tmp_path), "dataset")
    _ecrire_csv(
        dossier, "real.csv",
        ["title", "text"],
        [["", "Un corps sans titre"]],
    )

    rapport = ImportateurDataset(base).importer(dossier=dossier)

    assert rapport["lignes_ignorees"] == 0
    assert rapport["total_importes"] == 1
    articles = base.recuperer_articles_reference()
    assert articles[0]["titre"] == "Un corps sans titre"
    assert articles[0]["contenu"] == "Un corps sans titre"


# -------------------------------------------------------------
#  Rapport de comptage global
# -------------------------------------------------------------

def test_rapport_comptage_fake_et_real(tmp_path):
    """Le rapport agrège correctement les compteurs par étiquette sur
    plusieurs fichiers reconnus."""
    base, _ = ouvrir_base_temporaire(tmp_path)
    dossier = os.path.join(str(tmp_path), "dataset")
    _ecrire_csv(
        dossier, "Fake.csv",
        ["title", "text", "subject"],
        [["F1", "c1", "s"], ["F2", "c2", "s"]],
    )
    _ecrire_csv(
        dossier, "True.csv",
        ["title", "text", "subject"],
        [["R1", "c1", "s"], ["R2", "c2", "s"], ["R3", "c3", "s"]],
    )

    rapport = ImportateurDataset(base).importer(dossier=dossier)

    assert rapport["importes"]["fake"] == 2
    assert rapport["importes"]["real"] == 3
    assert rapport["total_importes"] == 5
    assert rapport["lignes_ignorees"] == 0
    assert rapport["fichiers_ignores"] == []
    assert rapport["erreurs"] == []


def test_fichier_nom_non_reconnu_est_ignore(tmp_path):
    """Un fichier .csv au nom non reconnu est comptabilisé dans
    fichiers_ignores sans qu'aucune de ses lignes soit importée
    (Req 1.7, cohérent avec l'étiquetage par fichier)."""
    base, _ = ouvrir_base_temporaire(tmp_path)
    dossier = os.path.join(str(tmp_path), "dataset")
    _ecrire_csv(
        dossier, "Fake.csv",
        ["title", "text"],
        [["F1", "c1"]],
    )
    _ecrire_csv(
        dossier, "autre.csv",
        ["title", "text"],
        [["X1", "c1"], ["X2", "c2"]],
    )

    rapport = ImportateurDataset(base).importer(dossier=dossier)

    assert "autre.csv" in rapport["fichiers_ignores"]
    assert rapport["total_importes"] == 1
    assert rapport["importes"]["fake"] == 1
    # Les lignes du fichier ignoré ne sont jamais lues.
    assert base.compter_articles_reference() == 1


# -------------------------------------------------------------
#  Cas dossier introuvable (Req 1.6)
# -------------------------------------------------------------

def test_dossier_introuvable_aucun_import(tmp_path):
    """Dossier inexistant : aucun import, rapport à zéro et message
    indiquant l'emplacement attendu (Req 1.6)."""
    base, _ = ouvrir_base_temporaire(tmp_path)
    dossier_absent = os.path.join(str(tmp_path), "dossier_qui_nexiste_pas")

    rapport = ImportateurDataset(base).importer(dossier=dossier_absent)

    assert rapport["total_importes"] == 0
    assert rapport["importes"] == {"fake": 0, "real": 0}
    assert rapport["lignes_ignorees"] == 0
    # Le message mentionne le dossier attendu et reste informatif.
    assert dossier_absent in rapport["message"]
    assert base.compter_articles_reference() == 0


def test_aucun_csv_reconnu_avertissement(tmp_path):
    """Dossier présent mais sans fichier reconnu : avertissement listant
    les fichiers attendus, aucun import (Req 1.7)."""
    base, _ = ouvrir_base_temporaire(tmp_path)
    dossier = os.path.join(str(tmp_path), "dataset")
    _ecrire_csv(
        dossier, "inconnu.csv",
        ["title", "text"],
        [["X", "y"]],
    )

    rapport = ImportateurDataset(base).importer(dossier=dossier)

    assert rapport["total_importes"] == 0
    assert "inconnu.csv" in rapport["fichiers_ignores"]
    assert "Fake.csv" in rapport["message"]
    assert base.compter_articles_reference() == 0
