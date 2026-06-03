# =============================================================
#  Classe BaseDeDonnees
#  Fichier : classes/base_donnees.py
# =============================================================
#
#  Cette classe ajoute la PERSISTANCE locale au projet.
#  Sans elle, chaque analyse est perdue à la fermeture du
#  programme. Avec elle, on conserve une trace durable.
#
#  Elle s'appuie sur SQLite, via le module "sqlite3" intégré
#  à Python (aucun serveur à installer, aucune dépendance) :
#  toute la base tient dans un seul fichier sur le disque
#  (data/fakenews.db).
#
#  Quatre responsabilités principales :
#    1. Initialiser la base et son schéma au démarrage.
#    2. Enregistrer chaque analyse (article + score + verdict + détail).
#    3. Consulter l'historique des analyses (trié par date).
#    4. Préparer une table de référence d'articles fiables
#       (contenus_fiables) pour un usage FUTUR de similarité.
#
#  Principe de robustesse :
#    - chaque écriture est "transactionnelle" : commit() si tout
#      va bien, rollback() en cas de problème (aucune ligne
#      partielle ne subsiste) ;
#    - les erreurs SQLite sont encapsulées dans une exception
#      métier dédiée : ErreurBaseDeDonnees.

# "sqlite3" : le moteur de base de données intégré à Python.
import sqlite3

# "os" : pour manipuler les dossiers (créer le dossier "data").
import os


# =============================================================
#  Exception métier : ErreurBaseDeDonnees
# =============================================================
#
#  On définit notre propre type d'erreur. Avantage : le menu
#  console (main.py) peut intercepter spécifiquement les
#  problèmes de base de données, sans avoir à connaître les
#  détails internes de sqlite3.
#
#  Le message identifie l'opération concernée (connexion,
#  enregistrement, historique...) et la nature de l'erreur.

class ErreurBaseDeDonnees(Exception):
    """Erreur explicite signalée à l'appelant.

    Le message identifie l'opération concernée et la nature de
    l'erreur SQLite sous-jacente. Le menu console peut ainsi
    afficher un avertissement lisible et poursuivre l'exécution.
    """
    pass


class BaseDeDonnees:

    # ---------------------------------------------------------
    #  __init__ : ouvre (ou crée) la base et son schéma
    # ---------------------------------------------------------
    #  Étapes :
    #    1. Créer le dossier "data" s'il n'existe pas encore.
    #    2. Ouvrir la connexion SQLite vers le fichier de base.
    #    3. Créer les tables (analyses, contenus_fiables) si
    #       elles n'existent pas déjà.
    #
    #  Si le fichier et les tables existent déjà, on NE touche
    #  à rien : les lignes existantes sont conservées (on utilise
    #  CREATE TABLE IF NOT EXISTS, jamais DROP).
    #
    #  En cas d'échec (dossier non créable, connexion impossible,
    #  schéma non créable), on lève ErreurBaseDeDonnees.

    def __init__(self, chemin="data/fakenews.db"):

        # On mémorise le chemin du fichier de base.
        self.chemin = chemin

        # La connexion est mise à None au départ : si une étape
        # échoue, on saura qu'aucune connexion n'est ouverte.
        self.connexion = None

        # --- Étape 1 : créer le dossier "data" si nécessaire ---
        # os.path.dirname("data/fakenews.db") -> "data"
        dossier = os.path.dirname(chemin)
        if dossier:
            try:
                # exist_ok=True : pas d'erreur si le dossier existe déjà.
                os.makedirs(dossier, exist_ok=True)
            except OSError as e:
                # Impossible de créer le dossier (droits, chemin invalide...).
                raise ErreurBaseDeDonnees(
                    f"Initialisation : impossible de créer le dossier "
                    f"'{dossier}' ({e})"
                )

        # --- Étape 2 : ouvrir la connexion SQLite ---
        try:
            # sqlite3.connect crée le fichier s'il n'existe pas.
            self.connexion = sqlite3.connect(chemin)
        except sqlite3.Error as e:
            raise ErreurBaseDeDonnees(
                f"Initialisation : connexion impossible à '{chemin}' ({e})"
            )

        # --- Étape 3 : créer le schéma (les deux tables) ---
        # _creer_schema lève déjà ErreurBaseDeDonnees en cas d'échec.
        self._creer_schema()

    # ---------------------------------------------------------
    #  _creer_schema : crée les tables si elles n'existent pas
    # ---------------------------------------------------------
    #  La convention "_" indique une méthode "privée" : utilisée
    #  seulement en interne (ici par __init__).
    #
    #  On crée DEUX tables :
    #    - "analyses"         : l'historique des analyses.
    #    - "contenus_fiables" : la base de référence (usage FUTUR).
    #
    #  CREATE TABLE IF NOT EXISTS : ne recrée pas la table si elle
    #  existe déjà -> les données précédentes sont préservées.
    #
    #  L'opération est transactionnelle : si une création échoue,
    #  on annule (rollback) pour ne laisser aucune table partielle.

    def _creer_schema(self):

        # Table des analyses (voir Data Models du design).
        sql_analyses = """
            CREATE TABLE IF NOT EXISTS analyses (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                titre   TEXT    NOT NULL,
                contenu TEXT    NOT NULL,
                source  TEXT    NOT NULL DEFAULT 'Inconnue',
                date    TEXT    NOT NULL,
                score   INTEGER NOT NULL,
                verdict TEXT    NOT NULL,
                detail  TEXT
            )
        """

        # Table de référence des contenus fiables.
        #
        # NOTE : cette table prépare une fonctionnalité FUTURE.
        # Elle stockera des articles réputés fiables qui serviront
        # de référence pour un CALCUL DE SIMILARITÉ dans une phase
        # ultérieure du projet. Pour l'instant, on se contente de
        # la créer et de l'alimenter (aucune comparaison n'est faite).
        sql_contenus_fiables = """
            CREATE TABLE IF NOT EXISTS contenus_fiables (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                titre   TEXT NOT NULL,
                contenu TEXT NOT NULL,
                source  TEXT NOT NULL DEFAULT 'Inconnue'
            )
        """

        try:
            curseur = self.connexion.cursor()
            curseur.execute(sql_analyses)
            curseur.execute(sql_contenus_fiables)
            # On valide la création des tables.
            self.connexion.commit()
        except sqlite3.Error as e:
            # En cas d'échec, on annule toute transaction en cours
            # pour ne laisser aucune table partiellement créée.
            try:
                self.connexion.rollback()
            except sqlite3.Error:
                # Si même le rollback échoue, on continue vers la
                # levée de l'erreur métier (rien d'autre à faire).
                pass
            raise ErreurBaseDeDonnees(
                f"Création du schéma : échec de la création des tables ({e})"
            )

    # ---------------------------------------------------------
    #  _serialiser_detail : liste de lignes -> texte unique
    # ---------------------------------------------------------
    #  Le "detail" produit par la classe Score est une LISTE de
    #  lignes. Une colonne SQLite stocke du texte simple, donc on
    #  joint les lignes par des sauts de ligne ("\n").
    #
    #  Exemple :
    #    ["Score de base : 50", "+20 sources citées"]
    #      -> "Score de base : 50\n+20 sources citées"

    def _serialiser_detail(self, detail):

        # Si le détail est absent (None), on stocke une chaîne vide.
        if detail is None:
            return ""

        # "\n".join assemble toutes les lignes en un seul texte.
        return "\n".join(detail)

    # ---------------------------------------------------------
    #  _deserialiser_detail : texte unique -> liste de lignes
    # ---------------------------------------------------------
    #  Opération inverse de _serialiser_detail : on redécoupe le
    #  texte sur les sauts de ligne pour retrouver la liste.
    #
    #  Exemple :
    #    "Score de base : 50\n+20 sources citées"
    #      -> ["Score de base : 50", "+20 sources citées"]

    def _deserialiser_detail(self, texte):

        # Une chaîne vide ou None correspond à une liste vide.
        if not texte:
            return []

        # split("\n") redécoupe exactement sur les sauts de ligne,
        # ce qui préserve l'intégralité des lignes et leur ordre.
        return texte.split("\n")

    # ---------------------------------------------------------
    #  _normaliser_source : remplace une source absente
    # ---------------------------------------------------------
    #  Règle commune aux analyses et aux contenus fiables :
    #  une source nulle, vide ou composée uniquement d'espaces
    #  devient "Inconnue".

    def _normaliser_source(self, source):

        # None ou chaîne vide / espaces uniquement -> "Inconnue".
        if source is None or str(source).strip() == "":
            return "Inconnue"
        return source

    # ---------------------------------------------------------
    #  enregistrer_analyse : insère une analyse dans "analyses"
    # ---------------------------------------------------------
    #  Entrées :
    #    article  : un Article (titre, contenu, source, date).
    #    resultat : un dict {"score", "verdict", "detail"} produit
    #               par Score.calculer().
    #
    #  Sortie : l'identifiant (entier strictement positif) de la
    #           ligne créée.
    #
    #  Comportement transactionnel :
    #    - succès -> commit() puis on retourne l'id ;
    #    - échec  -> rollback() (aucune ligne résiduelle) puis on
    #                lève ErreurBaseDeDonnees, sans retourner d'id.

    def enregistrer_analyse(self, article, resultat):

        # --- Préparation des valeurs à insérer ---

        # Source normalisée : None / vide / espaces -> "Inconnue".
        source = self._normaliser_source(article.source)

        # Date formatée depuis l'attribut datetime de l'article,
        # au format texte canonique "AAAA-MM-JJ HH:MM:SS"
        # (cohérent avec Article.to_dict()).
        date_texte = article.date.strftime("%Y-%m-%d %H:%M:%S")

        # Détail (liste de lignes) sérialisé en texte unique.
        detail_texte = self._serialiser_detail(resultat["detail"])

        sql = """
            INSERT INTO analyses (titre, contenu, source, date, score, verdict, detail)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """

        valeurs = (
            article.titre,
            article.contenu,
            source,
            date_texte,
            resultat["score"],
            resultat["verdict"],
            detail_texte,
        )

        try:
            curseur = self.connexion.cursor()
            curseur.execute(sql, valeurs)
            # On valide : la donnée est durablement écrite sur disque.
            self.connexion.commit()
            # lastrowid = l'identifiant auto-incrémenté de la ligne
            # qu'on vient d'insérer (toujours strictement positif).
            return curseur.lastrowid
        except sqlite3.Error as e:
            # Échec (y compris fichier verrouillé) : on annule tout
            # pour garantir qu'aucune ligne ne subsiste.
            try:
                self.connexion.rollback()
            except sqlite3.Error:
                pass
            # On signale l'échec sans retourner d'identifiant.
            # L'erreur est récupérable : le programme peut continuer.
            raise ErreurBaseDeDonnees(
                f"Enregistrement d'une analyse : échec de l'écriture ({e})"
            )

    # ---------------------------------------------------------
    #  recuperer_historique : lit les analyses enregistrées
    # ---------------------------------------------------------
    #  Tri : par date décroissante (la plus récente en premier),
    #        puis à dates égales par id décroissant.
    #
    #  Paramètre "limite" :
    #    - None    -> toutes les analyses ;
    #    - >= 1    -> au plus "limite" analyses (toutes si la
    #                 limite dépasse le nombre d'analyses) ;
    #    - < 1     -> ErreurBaseDeDonnees, aucune analyse retournée.
    #
    #  Sortie : liste de dict {id, titre, score, verdict, date}.

    def recuperer_historique(self, limite=None):

        # --- Validation de la limite ---
        # Une limite fournie mais strictement inférieure à 1 est
        # invalide : on signale l'erreur et on ne retourne rien.
        if limite is not None and limite < 1:
            raise ErreurBaseDeDonnees(
                f"Récupération de l'historique : limite invalide ({limite}), "
                f"elle doit être supérieure ou égale à 1"
            )

        # On ne sélectionne que les colonnes utiles à l'affichage.
        sql = """
            SELECT id, titre, score, verdict, date
            FROM analyses
            ORDER BY date DESC, id DESC
        """

        # Si une limite valide est fournie, on l'ajoute à la requête.
        # On passe la valeur en paramètre (?) pour éviter toute
        # injection et garder une requête sûre.
        parametres = ()
        if limite is not None:
            sql += " LIMIT ?"
            parametres = (limite,)

        try:
            curseur = self.connexion.cursor()
            curseur.execute(sql, parametres)
            lignes = curseur.fetchall()
        except sqlite3.Error as e:
            raise ErreurBaseDeDonnees(
                f"Récupération de l'historique : échec de la lecture ({e})"
            )

        # On transforme chaque tuple SQL en dictionnaire lisible.
        historique = []
        for ligne in lignes:
            historique.append({
                "id":      ligne[0],
                "titre":   ligne[1],
                "score":   ligne[2],
                "verdict": ligne[3],
                "date":    ligne[4],
            })

        return historique

    # ---------------------------------------------------------
    #  ajouter_contenu_fiable : alimente la base de référence
    # ---------------------------------------------------------
    #  Insère un article réputé fiable dans "contenus_fiables".
    #
    #  NOTE (usage FUTUR) : ces contenus serviront de RÉFÉRENCE
    #  pour un CALCUL DE SIMILARITÉ dans une phase ultérieure du
    #  projet. Pour l'instant, on se contente de les stocker ;
    #  aucune comparaison n'est encore effectuée.
    #
    #  Source absente (None / vide / espaces) -> "Inconnue".
    #
    #  Sortie : l'identifiant créé (entier strictement positif).
    #  commit() en cas de succès, rollback() + ErreurBaseDeDonnees
    #  en cas d'échec.

    def ajouter_contenu_fiable(self, titre, contenu, source=None):
        """Ajoute un article de référence dans `contenus_fiables`.

        NOTE : l'exploitation par similarité est prévue pour une phase
        ultérieure du projet. Pour l'instant, ces contenus sont
        seulement stockés (aucune comparaison n'est encore effectuée).
        Retour : int (identifiant créé). commit en cas de succès,
        rollback + ErreurBaseDeDonnees en cas d'échec.
        """

        # Source normalisée comme pour les analyses.
        source = self._normaliser_source(source)

        sql = """
            INSERT INTO contenus_fiables (titre, contenu, source)
            VALUES (?, ?, ?)
        """

        try:
            curseur = self.connexion.cursor()
            curseur.execute(sql, (titre, contenu, source))
            self.connexion.commit()
            return curseur.lastrowid
        except sqlite3.Error as e:
            try:
                self.connexion.rollback()
            except sqlite3.Error:
                pass
            raise ErreurBaseDeDonnees(
                f"Ajout d'un contenu fiable : échec de l'écriture ({e})"
            )

    # ---------------------------------------------------------
    #  recuperer_contenus_fiables : lit la base de référence
    # ---------------------------------------------------------
    #  Sortie : liste de dict {id, titre, contenu, source}.
    #  Liste vide si aucun contenu n'a été enregistré.

    def recuperer_contenus_fiables(self):

        sql = """
            SELECT id, titre, contenu, source
            FROM contenus_fiables
            ORDER BY id
        """

        try:
            curseur = self.connexion.cursor()
            curseur.execute(sql)
            lignes = curseur.fetchall()
        except sqlite3.Error as e:
            raise ErreurBaseDeDonnees(
                f"Récupération des contenus fiables : échec de la lecture ({e})"
            )

        contenus = []
        for ligne in lignes:
            contenus.append({
                "id":      ligne[0],
                "titre":   ligne[1],
                "contenu": ligne[2],
                "source":  ligne[3],
            })

        return contenus

    # ---------------------------------------------------------
    #  fermer : ferme la connexion SQLite active
    # ---------------------------------------------------------
    #  À appeler avant de quitter le programme pour libérer
    #  proprement le fichier de base.

    def fermer(self):

        # On ne ferme que si une connexion est effectivement ouverte.
        if self.connexion is not None:
            self.connexion.close()
            self.connexion = None
