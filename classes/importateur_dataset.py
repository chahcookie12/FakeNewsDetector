# =============================================================
#  Classe ImportateurDataset
#  Fichier : classes/importateur_dataset.py
# =============================================================
#
#  Cet importateur alimente la BASE DE RÉFÉRENCE d'articles
#  étiquetés (fake / real) à partir des fichiers CSV du jeu de
#  données Kaggle ISOT « Fake and Real News », placés dans
#  data/dataset/.
#
#  Particularité importante : l'étiquette (fake / real) n'est
#  PAS lue dans une colonne du CSV. Elle est DÉDUITE du NOM du
#  fichier d'origine :
#    - Fake.csv               -> "fake"
#    - real.csv  ou  True.csv -> "real"
#    - tout autre nom         -> ignoré (aucune étiquette)
#
#  Ce fichier contient les FONCTIONS UTILITAIRES de bas niveau
#  (déduction d'étiquette, mapping souple des colonnes, combinaison
#  titre + texte) ainsi que la classe ImportateurDataset qui réalise
#  l'IMPORT PAR LOT complet (méthode `importer`) et produit un
#  rapport de synthèse.
#
#  Conventions respectées (cohérence avec le reste du projet) :
#    - comparaisons de noms et de colonnes INSENSIBLES À LA CASSE ;
#    - suppression des espaces de début / fin (strip) ;
#    - source absente / vide normalisée en "Inconnue".


# "os"  : pour parcourir le dossier du jeu de données.
# "csv" : pour lire les fichiers CSV ligne par ligne (DictReader).
import os
import csv

# On réutilise l'exception métier de la persistance pour intercepter
# proprement les échecs d'écriture ligne par ligne sans interrompre
# l'import du reste du jeu de données.
from classes.base_donnees import ErreurBaseDeDonnees


# -------------------------------------------------------------
#  Constantes de mapping (déclarées une fois, réutilisées)
# -------------------------------------------------------------
#  L'étiquette n'appartient qu'à l'ensemble { "fake", "real" }.
#  On associe chaque NOM DE FICHIER reconnu (comparé en minuscules)
#  à son étiquette. Tout nom absent de ce dictionnaire est ignoré.
ETIQUETTES_PAR_FICHIER = {
    "fake.csv": "fake",
    "real.csv": "real",
    "true.csv": "real",
}

# Noms de colonnes acceptés pour le TITRE, par ordre de priorité.
# "title" est prioritaire sur "titre" si les deux sont présents.
COLONNES_TITRE = ("title", "titre")

# Noms de colonnes acceptés pour le CONTENU, par ordre de priorité.
# "text" est prioritaire sur "contenu" si les deux sont présents.
COLONNES_CONTENU = ("text", "contenu")

# Nom de colonne accepté pour la SOURCE (sujet de l'article).
COLONNE_SOURCE = "subject"

# Valeur par défaut de la source lorsqu'elle est absente ou vide.
SOURCE_PAR_DEFAUT = "Inconnue"


# -------------------------------------------------------------
#  deduire_etiquette : nom de fichier -> "fake" / "real" / None
# -------------------------------------------------------------
#  Entrée :
#    nom_fichier : le nom COMPLET du fichier (extension .csv
#                  comprise, sans le chemin de dossier),
#                  par exemple "Fake.csv" ou "REAL.CSV".
#
#  Comportement :
#    - comparaison INSENSIBLE À LA CASSE sur le nom complet ;
#    - "Fake.csv"            -> "fake"
#    - "real.csv" / "True.csv" -> "real"
#    - tout autre nom        -> None (le fichier est à ignorer).
#
#  On renvoie None (et pas une exception) pour les noms non
#  reconnus : l'appelant pourra alors comptabiliser le fichier
#  parmi les fichiers ignorés du rapport (exigence 2.5).

def deduire_etiquette(nom_fichier):
    """Déduit l'étiquette (`fake`/`real`) à partir du nom de fichier.

    La comparaison est insensible à la casse et porte sur le nom
    complet (extension `.csv` comprise). Renvoie ``None`` pour tout
    nom non reconnu, afin que l'appelant puisse ignorer le fichier.
    """

    # Un nom absent (None) ou vide ne correspond à aucun fichier connu.
    if not nom_fichier:
        return None

    # On retire les espaces parasites puis on compare en minuscules.
    cle = str(nom_fichier).strip().lower()

    # .get renvoie l'étiquette associée, ou None si le nom est inconnu.
    return ETIQUETTES_PAR_FICHIER.get(cle)


# -------------------------------------------------------------
#  _normaliser_entetes : prépare un index colonne -> nom normalisé
# -------------------------------------------------------------
#  Le mapping des colonnes doit être souple : on tolère les
#  espaces de début / fin et la casse. Cette fonction interne
#  construit, à partir des en-têtes réels du CSV, un dictionnaire
#  qui associe le NOM NORMALISÉ (strip + minuscules) au NOM RÉEL
#  de la colonne tel qu'il apparaît dans la ligne du CSV.
#
#  Exemple :
#    [" Title ", "TEXT", "Subject"]
#      -> { "title": " Title ", "text": "TEXT", "subject": "Subject" }
#
#  Si deux en-têtes se normalisent vers le même nom, on conserve
#  le PREMIER rencontré (comportement déterministe).

def _normaliser_entetes(noms_colonnes):

    index = {}
    for nom in noms_colonnes:
        # Un en-tête None est ignoré (robustesse).
        if nom is None:
            continue
        cle = str(nom).strip().lower()
        # On ne garde que la première occurrence d'un nom normalisé.
        if cle not in index:
            index[cle] = nom
    return index


# -------------------------------------------------------------
#  _premiere_valeur : récupère la valeur de la 1re colonne trouvée
# -------------------------------------------------------------
#  Entrées :
#    ligne          : un dict {nom_colonne_reel: valeur} (une ligne CSV).
#    index_entetes  : le dict produit par _normaliser_entetes.
#    noms_candidats : noms acceptés, PAR ORDRE DE PRIORITÉ
#                     (ex. ("title", "titre")).
#
#  Comportement :
#    - on parcourt les noms candidats DANS L'ORDRE : le premier
#      présent dans l'index l'emporte (gestion de la priorité) ;
#    - la valeur lue est nettoyée (strip) ;
#    - si aucune colonne candidate n'est présente, on renvoie "".

def _premiere_valeur(ligne, index_entetes, noms_candidats):

    for candidat in noms_candidats:
        # candidat est déjà en minuscules dans les constantes.
        if candidat in index_entetes:
            nom_reel = index_entetes[candidat]
            valeur = ligne.get(nom_reel)
            # Une valeur None devient une chaîne vide.
            if valeur is None:
                return ""
            return str(valeur).strip()
    # Aucune des colonnes candidates n'existe dans cette ligne.
    return ""


# -------------------------------------------------------------
#  extraire_champs : ligne CSV -> (titre, contenu, source)
# -------------------------------------------------------------
#  Applique le mapping souple des colonnes à une ligne de CSV.
#
#  Entrées :
#    ligne         : un dict {nom_colonne_reel: valeur}.
#    index_entetes : index optionnel (voir _normaliser_entetes).
#                    S'il n'est pas fourni, il est reconstruit à
#                    partir des clés de la ligne (pratique pour un
#                    appel isolé / les tests).
#
#  Sortie : un tuple (titre, contenu, source) où :
#    - titre   : valeur de "title"/"titre" (priorité "title"), strippée ;
#    - contenu : valeur de "text"/"contenu" (priorité "text"), strippée ;
#    - source  : valeur de "subject" si présente et non vide après
#                strip, sinon "Inconnue".

def extraire_champs(ligne, index_entetes=None):
    """Extrait `(titre, contenu, source)` d'une ligne CSV (mapping souple)."""

    # Si l'index n'est pas fourni, on le construit depuis les clés.
    if index_entetes is None:
        index_entetes = _normaliser_entetes(ligne.keys())

    # Titre et contenu via leurs colonnes candidates prioritaires.
    titre = _premiere_valeur(ligne, index_entetes, COLONNES_TITRE)
    contenu = _premiere_valeur(ligne, index_entetes, COLONNES_CONTENU)

    # Source : colonne "subject" si présente ET non vide après strip,
    # sinon valeur par défaut "Inconnue".
    source = _premiere_valeur(ligne, index_entetes, (COLONNE_SOURCE,))
    if source == "":
        source = SOURCE_PAR_DEFAUT

    return titre, contenu, source


# -------------------------------------------------------------
#  combiner_titre_texte : titre + texte -> contenu de référence
# -------------------------------------------------------------
#  Règle (exigence 1.2) :
#    - on concatène le titre PUIS le texte, séparés par un saut
#      de ligne ("\n") ;
#    - si l'un des deux champs est vide (après strip), on n'utilise
#      QUE le champ non vide, sans saut de ligne superflu.
#
#  Exemples :
#    ("Titre", "Corps")  -> "Titre\nCorps"
#    ("Titre", "")        -> "Titre"
#    ("",      "Corps")  -> "Corps"
#    ("",      "")        -> ""

def combiner_titre_texte(titre, texte):
    """Combine titre et texte en un contenu unique (titre puis texte).

    Les deux champs sont séparés par un saut de ligne. Lorsqu'un des
    champs est vide, seul le champ non vide est conservé.
    """

    # On nettoie les deux champs (robustesse, même si déjà strippés).
    titre = (titre or "").strip()
    texte = (texte or "").strip()

    # On ne garde que les morceaux non vides, dans l'ordre titre, texte.
    morceaux = [m for m in (titre, texte) if m]

    # join évite tout "\n" superflu lorsqu'un seul morceau est présent.
    return "\n".join(morceaux)


# -------------------------------------------------------------
#  Liste des noms de fichiers reconnus (pour les avertissements)
# -------------------------------------------------------------
#  Sert uniquement à composer un message lisible lorsqu'aucun
#  fichier reconnu n'est trouvé (exigence 1.7). Les clés de
#  ETIQUETTES_PAR_FICHIER sont en minuscules ; on présente ici des
#  noms tels que l'utilisateur les attend dans data/dataset/.
FICHIERS_ATTENDUS = ("Fake.csv", "real.csv", "True.csv")

# Dossier par défaut où l'utilisateur place les fichiers du jeu ISOT.
DOSSIER_PAR_DEFAUT = "data/dataset/"


# =============================================================
#  Classe ImportateurDataset
# =============================================================
#
#  Réalise l'IMPORT PAR LOT des fichiers CSV du jeu ISOT vers la
#  table de référence étiquetée (articles_reference), via une
#  instance de BaseDeDonnees fournie à la construction.
#
#  L'import est PONCTUEL (action de menu) : il n'est pas exécuté à
#  chaque lancement. Il applique la philosophie de DÉGRADATION
#  GRACIEUSE déjà en place dans le projet :
#    - dossier introuvable -> rapport explicatif, aucun import ;
#    - aucun CSV reconnu   -> avertissement listant les fichiers
#                             attendus, sans interrompre le programme ;
#    - fichier illisible    -> comptabilisé en erreur, on poursuit ;
#    - ligne sans titre/contenu exploitable -> ignorée et comptée.

class ImportateurDataset:

    # ---------------------------------------------------------
    #  __init__ : mémorise la base de référence cible
    # ---------------------------------------------------------
    #  Entrée :
    #    base : une instance BaseDeDonnees ouverte. C'est par elle
    #           que chaque ligne valide est insérée via
    #           ajouter_article_reference.

    def __init__(self, base):
        # On conserve la référence vers la persistance : l'import
        # délègue toutes les écritures à cette instance.
        self.base = base

    # ---------------------------------------------------------
    #  _rapport_vide : structure de rapport initialisée à zéro
    # ---------------------------------------------------------
    #  Le rapport agrège tous les compteurs de l'import :
    #    - importes        : nombre d'articles importés PAR étiquette ;
    #    - total_importes  : total des lignes importées avec succès ;
    #    - lignes_ignorees : lignes sans titre/contenu exploitable ;
    #    - fichiers_ignores: noms des fichiers de nom non reconnu ;
    #    - erreurs         : fichiers illisibles/corrompus (nom + cause) ;
    #    - message         : synthèse lisible destinée à l'affichage.

    def _rapport_vide(self):
        return {
            "importes": {"fake": 0, "real": 0},
            "total_importes": 0,
            "lignes_ignorees": 0,
            "fichiers_ignores": [],
            "erreurs": [],
            "message": "",
        }

    # ---------------------------------------------------------
    #  importer : import par lot complet + rapport de synthèse
    # ---------------------------------------------------------
    #  Entrée :
    #    dossier : chemin du dossier contenant les CSV (par défaut
    #              "data/dataset/"). Seuls les fichiers présents
    #              DIRECTEMENT dans ce dossier sont lus (pas de
    #              parcours récursif des sous-dossiers).
    #
    #  Sortie : le rapport (dict) décrit dans _rapport_vide.
    #
    #  Comportement :
    #    - dossier introuvable -> rapport avec message d'emplacement
    #      attendu, sans aucun import (exigence 1.6) ;
    #    - chaque entrée .csv reconnue est importée ligne par ligne ;
    #    - un fichier de nom non reconnu est compté dans
    #      fichiers_ignores et n'est pas lu (exigences 2.5, 1.1) ;
    #    - un fichier illisible/corrompu est compté dans erreurs,
    #      puis on poursuit avec les autres (exigence 1.4) ;
    #    - aucun CSV reconnu/lisible -> avertissement listant les
    #      fichiers attendus (exigence 1.7).

    def importer(self, dossier=DOSSIER_PAR_DEFAUT):
        """Importe par lot les CSV du jeu ISOT et retourne un rapport.

        Lit les fichiers `.csv` présents directement dans `dossier`
        (sans sous-dossiers), déduit l'étiquette du nom de fichier,
        insère chaque ligne valide via `ajouter_article_reference`, et
        comptabilise lignes ignorées, fichiers ignorés et erreurs.
        """

        rapport = self._rapport_vide()

        # --- Exigence 1.6 : dossier introuvable ---
        # On ne tente aucun import et on indique où placer les CSV.
        if not os.path.isdir(dossier):
            rapport["message"] = (
                f"Dossier introuvable : '{dossier}'. Placez les fichiers CSV "
                f"du jeu de référence ({', '.join(FICHIERS_ATTENDUS)}) dans "
                f"ce dossier, puis relancez l'import."
            )
            return rapport

        # --- Lister les fichiers .csv DIRECTEMENT dans le dossier ---
        # os.listdir ne descend pas dans les sous-dossiers : on filtre
        # en plus pour ne garder que les fichiers (pas les dossiers) et
        # uniquement l'extension .csv (comparaison insensible à la casse).
        entrees_csv = []
        for nom in sorted(os.listdir(dossier)):
            chemin = os.path.join(dossier, nom)
            if not os.path.isfile(chemin):
                # Un sous-dossier nommé "x.csv" ne doit pas être lu.
                continue
            if nom.strip().lower().endswith(".csv"):
                entrees_csv.append(nom)

        # Compteur de fichiers reconnus ET effectivement traités sans
        # erreur de lecture : sert à détecter le cas "aucun CSV reconnu
        # lisible" (exigence 1.7).
        fichiers_reconnus_lus = 0

        for nom in entrees_csv:
            # --- Étiquette déduite du NOM de fichier uniquement ---
            etiquette = deduire_etiquette(nom)

            # Nom non reconnu : on ignore le fichier sans le lire et on
            # le comptabilise parmi les fichiers ignorés (exigence 2.5).
            if etiquette is None:
                rapport["fichiers_ignores"].append(nom)
                continue

            chemin = os.path.join(dossier, nom)

            # --- Lecture du fichier reconnu ---
            # Tout problème de lecture/décodage rend le fichier illisible :
            # on le compte en erreur et on poursuit (exigence 1.4).
            try:
                self._importer_fichier(chemin, etiquette, rapport)
                fichiers_reconnus_lus += 1
            except (OSError, csv.Error, UnicodeError) as e:
                rapport["erreurs"].append({
                    "fichier": nom,
                    "cause": str(e),
                })

        # --- Exigence 1.7 : aucun CSV reconnu présent ou lisible ---
        # Si aucun fichier reconnu n'a pu être lu, on retourne un
        # avertissement listant les fichiers attendus, sans planter.
        if fichiers_reconnus_lus == 0:
            rapport["message"] = (
                f"Aucun fichier CSV de référence reconnu n'a pu être importé "
                f"depuis '{dossier}'. Fichiers attendus : "
                f"{', '.join(FICHIERS_ATTENDUS)}."
            )
            return rapport

        # --- Synthèse de l'import réussi ---
        rapport["message"] = (
            f"Import terminé : {rapport['total_importes']} article(s) importé(s) "
            f"({rapport['importes']['fake']} fake, "
            f"{rapport['importes']['real']} real), "
            f"{rapport['lignes_ignorees']} ligne(s) ignorée(s), "
            f"{len(rapport['fichiers_ignores'])} fichier(s) ignoré(s), "
            f"{len(rapport['erreurs'])} erreur(s)."
        )
        return rapport

    # ---------------------------------------------------------
    #  _importer_fichier : importe les lignes d'UN fichier CSV
    # ---------------------------------------------------------
    #  Entrées :
    #    chemin    : chemin complet du fichier CSV reconnu ;
    #    etiquette : "fake" ou "real" déduite du nom de fichier ;
    #    rapport   : le rapport en cours, mis à jour en place.
    #
    #  Comportement :
    #    - mapping souple des colonnes (titre/contenu/source) ;
    #    - ligne sans titre/contenu exploitable -> ignorée et comptée
    #      (exigence 3.5) ;
    #    - ligne valide -> insérée via ajouter_article_reference ;
    #      un échec d'écriture sur UNE ligne est comptabilisé en erreur
    #      mais n'interrompt pas la lecture du fichier.
    #
    #  Toute erreur de lecture/décodage du fichier (illisible/corrompu)
    #  remonte à l'appelant qui la comptabilisera comme erreur de fichier.

    def _importer_fichier(self, chemin, etiquette, rapport):

        # newline="" est recommandé par le module csv ; encoding utf-8-sig
        # tolère un éventuel BOM en tête de fichier (fréquent sous Windows).
        with open(chemin, "r", encoding="utf-8-sig", newline="") as flux:
            lecteur = csv.DictReader(flux)

            # On normalise les en-têtes une seule fois pour tout le fichier.
            # Un fichier sans en-tête (fieldnames vide) ne produit aucune
            # colonne exploitable : chaque ligne sera donc ignorée.
            entetes = lecteur.fieldnames or []
            index_entetes = _normaliser_entetes(entetes)

            # On accumule les lignes valides puis on les insère EN MASSE
            # (un seul commit). Un commit par ligne rendrait l'import du
            # jeu ISOT (des dizaines de milliers de lignes) extrêmement
            # lent à cause des flushs disque répétés.
            a_inserer = []

            for ligne in lecteur:
                # Extraction souple des champs (titre prioritaire sur titre,
                # text prioritaire sur contenu, subject -> source).
                titre, contenu, source = extraire_champs(ligne, index_entetes)

                # --- Exigence 3.5 : ligne sans titre/contenu exploitable ---
                # Le contenu de référence combine titre + texte. S'il est
                # vide (les deux champs manquants/vides), la ligne est
                # ignorée et comptée, puis on poursuit.
                contenu_reference = combiner_titre_texte(titre, contenu)
                if contenu_reference == "":
                    rapport["lignes_ignorees"] += 1
                    continue

                # Le titre stocké ne doit pas être vide (contrainte de la
                # base). Si la ligne n'a qu'un corps de texte sans titre,
                # on réutilise le contenu combiné comme titre de secours.
                titre_a_stocker = titre if titre else contenu_reference

                a_inserer.append(
                    (titre_a_stocker, contenu_reference, etiquette, source)
                )

        # --- Insertion EN MASSE via la base de référence ---
        # Une seule transaction pour tout le fichier. Un échec d'écriture
        # global est comptabilisé en erreur de fichier (remonté par la
        # méthode de lot), sans interrompre l'import des autres fichiers.
        if not a_inserer:
            return

        try:
            resultat = self.base.ajouter_articles_reference_par_lot(a_inserer)
            rapport["importes"][etiquette] += resultat["inserees"]
            rapport["total_importes"] += resultat["inserees"]
            # Les lignes rejetées par la validation de la base (rares ici,
            # déjà filtrées en amont) sont comptées comme ignorées.
            rapport["lignes_ignorees"] += resultat["ignorees"]
        except ErreurBaseDeDonnees as e:
            rapport["erreurs"].append({
                "fichier": os.path.basename(chemin),
                "cause": str(e),
            })
