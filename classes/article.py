# =============================================================
#  Classe Article
#  Fichier : classes/article.py
# =============================================================
#
#  Cette classe représente un article ou texte à analyser.
#  Elle stocke les informations de base : titre, contenu,
#  source et date.
#
#  On importe "datetime" pour pouvoir travailler avec les dates.
#  datetime est une bibliothèque intégrée à Python (pas besoin de pip).

from datetime import datetime


class Article:
    # ---------------------------------------------------------
    #  __init__ : le constructeur
    # ---------------------------------------------------------
    #  C'est la méthode qui s'exécute automatiquement quand on
    #  crée un nouvel Article. "self" représente l'objet lui-même.
    #
    #  Les paramètres avec "= None" sont optionnels :
    #  si on ne les donne pas, ils valent None par défaut.
    #
    #  Exemple d'utilisation :
    #    a = Article(titre="Vaccins", contenu="Les vaccins sont...", source="lemonde.fr")

    def __init__(self, titre, contenu, source=None, date=None):

        # On stocke le titre de l'article.
        # "self.titre" crée un attribut accessible depuis l'extérieur.
        self.titre = titre

        # On stocke le contenu (le texte complet de l'article).
        self.contenu = contenu

        # On stocke la source (site web, journal...).
        # Si l'utilisateur ne donne pas de source, on met "Inconnue".
        if source is None:
            self.source = "Inconnue"
        else:
            self.source = source

        # On stocke la date.
        # Si l'utilisateur ne donne pas de date, on prend
        # automatiquement la date et l'heure d'aujourd'hui.
        # datetime.now() retourne quelque chose comme : 2025-04-12 14:32:00
        if date is None:
            self.date = datetime.now()
        else:
            self.date = date

    # ---------------------------------------------------------
    #  to_dict : convertit l'article en dictionnaire Python
    # ---------------------------------------------------------
    #  Un dictionnaire c'est une structure { "clé": valeur }.
    #  C'est utile pour afficher, sauvegarder ou déboguer
    #  les données facilement.
    #
    #  Exemple de résultat :
    #    {
    #      "titre": "Vaccins",
    #      "contenu": "Les vaccins sont...",
    #      "source": "lemonde.fr",
    #      "date": "2025-04-12 14:32:00"
    #    }

    def to_dict(self):

        return {
            "titre":   self.titre,
            "contenu": self.contenu,
            "source":  self.source,
            # On convertit la date en texte avec strftime.
            # "%Y-%m-%d %H:%M:%S" est un format standard :
            # année-mois-jour heure:minute:seconde
            "date":    self.date.strftime("%Y-%m-%d %H:%M:%S")
        }

    # ---------------------------------------------------------
    #  __str__ : ce qui s'affiche quand on fait print(article)
    # ---------------------------------------------------------
    #  Sans cette méthode, print(article) afficherait quelque chose
    #  d'incompréhensible comme <classes.article.Article object at 0x...>
    #  Avec __str__, on contrôle ce qui s'affiche.

    def __str__(self):
        return (
            f"Titre   : {self.titre}\n"
            f"Source  : {self.source}\n"
            f"Date    : {self.date.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Contenu : {self.contenu[:100]}..."
            # [:100] prend seulement les 100 premiers caractères
            # pour ne pas tout afficher si le texte est long
        )