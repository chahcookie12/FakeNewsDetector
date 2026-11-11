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

        # Table de référence des articles ÉTIQUETÉS (fake / real).
        #
        # Contrairement à "contenus_fiables", cette table porte une
        # colonne "label" qui distingue strictement les articles
        # "fake" des articles "real". Elle alimente le moteur de
        # comparaison par similarité (TF-IDF + cosinus).
        #
        # La contrainte CHECK(label IN ('fake','real')) garantit au
        # niveau du schéma qu'aucune étiquette hors de cet ensemble
        # ne peut être stockée. La création reste idempotente
        # (CREATE TABLE IF NOT EXISTS) : les lignes existantes sont
        # préservées, jamais supprimées ni recréées.
        sql_articles_reference = """
            CREATE TABLE IF NOT EXISTS articles_reference (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                titre   TEXT NOT NULL,
                contenu TEXT NOT NULL,
                label   TEXT NOT NULL CHECK (label IN ('fake', 'real')),
                source  TEXT NOT NULL DEFAULT 'Inconnue'
            )
        """

        try:
            curseur = self.connexion.cursor()
            curseur.execute(sql_analyses)
            curseur.execute(sql_contenus_fiables)
            curseur.execute(sql_articles_reference)
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
    #  ajouter_article_reference : alimente la référence étiquetée
    # ---------------------------------------------------------
    #  Insère un article ÉTIQUETÉ (fake / real) dans la table
    #  "articles_reference". Ces articles servent de RÉFÉRENCE au
    #  moteur de comparaison par similarité (TF-IDF + cosinus).
    #
    #  Entrées :
    #    titre   : titre de l'article (non vide après strip).
    #    contenu : texte de l'article (non vide après strip).
    #    label   : étiquette appartenant STRICTEMENT à {fake, real}.
    #    source  : sujet/source ; absente -> "Inconnue".
    #
    #  Validations (avant toute écriture) :
    #    - label hors de {fake, real}  -> ErreurBaseDeDonnees ;
    #    - titre OU contenu vide après strip -> ErreurBaseDeDonnees.
    #  Dans ces deux cas, AUCUNE ligne n'est écrite.
    #
    #  Sortie : l'identifiant créé (entier strictement positif).
    #  commit() en cas de succès, rollback() + ErreurBaseDeDonnees
    #  en cas d'échec SQLite (aucune ligne partielle ne subsiste).

    def ajouter_article_reference(self, titre, contenu, label, source=None):
        """Ajoute un article de référence étiqueté dans
        `articles_reference`.

        Valide le label ({fake, real}) et le caractère non vide du
        titre et du contenu (après strip), normalise la source
        absente en "Inconnue", écrit en transactionnel et retourne
        l'identifiant strictement positif de la ligne créée.
        """

        # --- Validation de l'étiquette ---
        # Le label doit appartenir STRICTEMENT à l'ensemble autorisé.
        # On rejette toute autre valeur AVANT d'écrire quoi que ce soit.
        if label not in ("fake", "real"):
            raise ErreurBaseDeDonnees(
                f"Ajout d'un article de référence : étiquette invalide "
                f"({label!r}), elle doit appartenir à {{'fake', 'real'}}"
            )

        # --- Validation du titre et du contenu ---
        # Un titre ou un contenu vide après suppression des espaces
        # est rejeté (aucune ligne ne doit être écrite). On gère aussi
        # le cas None pour rester robuste.
        if titre is None or str(titre).strip() == "":
            raise ErreurBaseDeDonnees(
                "Ajout d'un article de référence : titre vide"
            )
        if contenu is None or str(contenu).strip() == "":
            raise ErreurBaseDeDonnees(
                "Ajout d'un article de référence : contenu vide"
            )

        # Source normalisée comme pour les analyses / contenus fiables.
        source = self._normaliser_source(source)

        sql = """
            INSERT INTO articles_reference (titre, contenu, label, source)
            VALUES (?, ?, ?, ?)
        """

        try:
            curseur = self.connexion.cursor()
            curseur.execute(sql, (titre, contenu, label, source))
            self.connexion.commit()
            return curseur.lastrowid
        except sqlite3.Error as e:
            try:
                self.connexion.rollback()
            except sqlite3.Error:
                pass
            raise ErreurBaseDeDonnees(
                f"Ajout d'un article de référence : échec de l'écriture ({e})"
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
    #  ajouter_articles_reference_par_lot : insertion EN MASSE
    # ---------------------------------------------------------
    #  Insère PLUSIEURS articles de référence en UNE SEULE
    #  transaction (un seul commit). C'est l'API à privilégier pour
    #  un import volumineux (jeu ISOT : des dizaines de milliers de
    #  lignes) : un commit par ligne forcerait autant de flushs
    #  disque (fsync) et rendrait l'import extrêmement lent.
    #
    #  Entrée :
    #    articles : itérable de tuples (titre, contenu, label, source).
    #               source peut être None (normalisée en "Inconnue").
    #
    #  Validation : chaque ligne dont le label n'appartient pas à
    #  {fake, real} ou dont le titre/contenu est vide après strip est
    #  IGNORÉE (comptée dans "ignorees") plutôt que de faire échouer
    #  tout le lot. On ne lève donc pas pour une ligne invalide.
    #
    #  Sortie : un dict {"inserees": int, "ignorees": int}.
    #
    #  Comportement transactionnel : commit() unique en fin de lot ;
    #  en cas d'erreur SQLite, rollback() complet puis
    #  ErreurBaseDeDonnees (aucune ligne partielle ne subsiste).

    def ajouter_articles_reference_par_lot(self, articles):
        """Insère un lot d'articles de référence en une transaction.

        Les lignes invalides (label hors {fake, real}, titre/contenu
        vide après strip) sont ignorées et comptées. Retourne un dict
        {inserees, ignorees}. commit unique en cas de succès ;
        rollback + ErreurBaseDeDonnees en cas d'échec SQLite.
        """

        sql = """
            INSERT INTO articles_reference (titre, contenu, label, source)
            VALUES (?, ?, ?, ?)
        """

        # On prépare d'abord toutes les valeurs valides en mémoire :
        # les lignes invalides sont écartées sans interrompre le lot.
        valeurs = []
        ignorees = 0
        for titre, contenu, label, source in articles:
            if label not in ("fake", "real"):
                ignorees += 1
                continue
            if titre is None or str(titre).strip() == "":
                ignorees += 1
                continue
            if contenu is None or str(contenu).strip() == "":
                ignorees += 1
                continue
            valeurs.append(
                (titre, contenu, label, self._normaliser_source(source))
            )

        if not valeurs:
            # Rien à insérer : aucune écriture, aucun commit nécessaire.
            return {"inserees": 0, "ignorees": ignorees}

        try:
            curseur = self.connexion.cursor()
            # executemany + commit UNIQUE : une seule transaction pour
            # tout le lot (rapide même sur des dizaines de milliers de
            # lignes).
            curseur.executemany(sql, valeurs)
            self.connexion.commit()
            return {"inserees": len(valeurs), "ignorees": ignorees}
        except sqlite3.Error as e:
            try:
                self.connexion.rollback()
            except sqlite3.Error:
                pass
            raise ErreurBaseDeDonnees(
                f"Ajout d'articles de référence par lot : "
                f"échec de l'écriture ({e})"
            )

    # ---------------------------------------------------------
    #  recuperer_articles_reference : lit la référence étiquetée
    # ---------------------------------------------------------
    #  Retourne TOUS les articles de la table "articles_reference"
    #  destinés au moteur de comparaison par similarité.
    #
    #  Tri : par id croissant (ORDER BY id), comme pour les
    #  contenus fiables, afin d'obtenir un ordre déterministe.
    #
    #  Sortie : liste de dict {id, titre, contenu, label, source}.
    #           Liste vide si aucun article de référence n'a été
    #           enregistré (Req. 4.8).

    def recuperer_articles_reference(self):
        """Retourne la liste des articles de référence étiquetés.

        Chaque entrée est un dict {id, titre, contenu, label,
        source}. La liste est vide lorsqu'aucun article de
        référence n'a été enregistré. Une erreur SQLite est
        encapsulée dans ErreurBaseDeDonnees.
        """

        sql = """
            SELECT id, titre, contenu, label, source
            FROM articles_reference
            ORDER BY id
        """

        try:
            curseur = self.connexion.cursor()
            curseur.execute(sql)
            lignes = curseur.fetchall()
        except sqlite3.Error as e:
            raise ErreurBaseDeDonnees(
                f"Récupération des articles de référence : "
                f"échec de la lecture ({e})"
            )

        articles = []
        for ligne in lignes:
            articles.append({
                "id":      ligne[0],
                "titre":   ligne[1],
                "contenu": ligne[2],
                "label":   ligne[3],
                "source":  ligne[4],
            })

        return articles

    # ---------------------------------------------------------
    #  compter_articles_reference : nombre d'articles de référence
    # ---------------------------------------------------------
    #  Méthode utilitaire : retourne le nombre de lignes présentes
    #  dans la table "articles_reference". Utile pour le réimport,
    #  les tests, et la détection d'une référence vide (un retour
    #  de 0 signifie qu'aucune comparaison par similarité n'est
    #  possible).
    #
    #  Sortie : entier >= 0 (0 si la référence est vide).

    def compter_articles_reference(self):
        """Retourne le nombre d'articles de référence enregistrés.

        Retourne 0 lorsque la table est vide. Une erreur SQLite est
        encapsulée dans ErreurBaseDeDonnees.
        """

        sql = "SELECT COUNT(*) FROM articles_reference"

        try:
            curseur = self.connexion.cursor()
            curseur.execute(sql)
            ligne = curseur.fetchone()
        except sqlite3.Error as e:
            raise ErreurBaseDeDonnees(
                f"Comptage des articles de référence : "
                f"échec de la lecture ({e})"
            )

        # fetchone() sur un COUNT(*) retourne toujours une ligne
        # (ex. (0,)) ; on extrait le premier champ.
        return ligne[0]

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
