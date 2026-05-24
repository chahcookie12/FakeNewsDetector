# =============================================================
#  Classe Analyseur
#  Fichier : classes/analyseur.py
# =============================================================
#
#  C'est le coeur du projet.
#  L'Analyseur prend un texte brut et en extrait des indicateurs
#  mesurables qu'on pourra ensuite utiliser pour calculer un score.
#
#  Pipeline complet :
#    texte brut
#      → nettoyage (ponctuation, minuscules)
#        → tokenisation (découpage en mots)
#          → suppression des stop words
#            → comptage des fréquences
#              → détection des mots suspects
#                → détection des sources
#                  → indicateurs finaux

# "re" est la bibliothèque des expressions régulières.
# Elle permet de chercher et supprimer des motifs dans un texte.
import re

# "Counter" est une classe spéciale qui compte automatiquement
# les occurrences dans une liste.
# Ex : Counter(["chat","chien","chat"]) → {"chat":2, "chien":1}
from collections import Counter


class Analyseur:

    # ---------------------------------------------------------
    #  Liste intégrée de stop words (fr + en)
    # ---------------------------------------------------------
    #  On les intègre directement dans le code pour ne pas dépendre
    #  d'une connexion internet au premier lancement.
    #  nltk.download() peut toujours être utilisé si vous êtes
    #  connectés — mais cette liste suffit pour le projet.

    STOP_WORDS = {
        # Français
        "le","la","les","de","du","des","un","une","et","est","en",
        "au","aux","ce","se","sa","son","ses","mon","ton","que","qui",
        "ne","pas","plus","par","sur","dans","avec","pour","mais","ou",
        "donc","or","ni","car","je","tu","il","elle","nous","vous","ils",
        "elles","me","te","lui","leur","y","on","si","tout","très","bien",
        "aussi","comme","quand","dont","où","même","après","avant","sans",
        "sous","entre","vers","chez","lors","dès","cet","cette","ces",
        "être","avoir","faire","dit","été","selon","ainsi","alors",
        # Anglais
        "the","a","an","and","or","but","in","on","at","to","for",
        "of","with","by","from","is","are","was","were","be","been",
        "has","have","had","do","does","did","not","this","that",
        "it","its","we","you","he","she","they","their","our","your",
        "his","her","as","if","so","up","out","about","than","more",
        "also","just","can","will","would","could","should","may",
    }

    # ---------------------------------------------------------
    #  __init__ : prépare l'analyseur au démarrage
    # ---------------------------------------------------------

    def __init__(self, chemin_mots_suspects="data/mots_suspects.txt"):

        # On charge les mots suspects depuis le fichier texte
        self.mots_suspects = self._charger_mots_suspects(chemin_mots_suspects)

    # ---------------------------------------------------------
    #  _charger_mots_suspects : lit data/mots_suspects.txt
    # ---------------------------------------------------------
    #  La convention "_" devant le nom = méthode "privée",
    #  utilisée seulement en interne par la classe.
    #
    #  Le fichier contient un mot par ligne.
    #  Les lignes qui commencent par "#" sont des commentaires.

    def _charger_mots_suspects(self, chemin):

        mots = set()  # set = pas de doublons, recherche rapide

        try:
            with open(chemin, "r", encoding="utf-8") as f:
                for ligne in f:
                    ligne = ligne.strip()          # retire \n et espaces
                    if ligne and not ligne.startswith("#"):
                        mots.add(ligne.lower())    # tout en minuscules

        except FileNotFoundError:
            # Si le fichier n'existe pas, liste de secours minimale
            print(f"[Analyseur] '{chemin}' introuvable. Liste minimale utilisée.")
            mots = {"urgent","choc","incroyable","scandale",
                    "exclusif","alerte","secret","complot"}

        return mots

    # ---------------------------------------------------------
    #  nettoyer : prépare le texte brut pour l'analyse
    # ---------------------------------------------------------
    #  Entrée  : "Les VACCINS causent l'autisme, CHOC !"
    #  Sortie  : "les vaccins causent lautisme choc"

    def nettoyer(self, texte):

        # Étape 1 : tout en minuscules
        texte = texte.lower()

        # Étape 2 : supprimer la ponctuation et caractères spéciaux
        # [^\w\s] = tout ce qui n'est pas lettre/chiffre ou espace
        texte = re.sub(r"[^\w\s]", " ", texte)

        # Étape 3 : supprimer les chiffres isolés
        texte = re.sub(r"\b\d+\b", "", texte)

        # Étape 4 : supprimer les espaces multiples
        texte = re.sub(r"\s+", " ", texte).strip()

        return texte

    # ---------------------------------------------------------
    #  tokeniser : découpe le texte en liste de mots
    # ---------------------------------------------------------
    #  "Tokeniser" = découper en unités de base appelées "tokens".
    #
    #  Entrée  : "les vaccins causent lautisme choc"
    #  Sortie  : ["les", "vaccins", "causent", "lautisme", "choc"]

    def tokeniser(self, texte_nettoye):

        # .split() découpe sur les espaces
        tokens = texte_nettoye.split()

        # On garde seulement les mots de 2 lettres ou plus.
        # Ça élimine les lettres isolées comme "l" ou "d".
        tokens = [mot for mot in tokens if len(mot) >= 2]

        return tokens

    # ---------------------------------------------------------
    #  supprimer_stop_words : enlève les mots sans intérêt
    # ---------------------------------------------------------
    #  Entrée  : ["les", "vaccins", "sont", "dangereux"]
    #  Sortie  : ["vaccins", "dangereux"]
    #
    #  On utilise une "list comprehension" — façon compacte
    #  d'écrire une boucle qui construit une liste filtrée.

    def supprimer_stop_words(self, tokens):

        return [mot for mot in tokens if mot not in self.STOP_WORDS]

    # ---------------------------------------------------------
    #  compter_frequences : compte les occurrences de chaque mot
    # ---------------------------------------------------------
    #  Entrée  : ["vaccin","vaccin","sante","vaccin","choc"]
    #  Sortie  : {"vaccin": 3, "choc": 1, "sante": 1}
    #
    #  top_n = combien de mots on retourne (les plus fréquents)

    def compter_frequences(self, tokens, top_n=10):

        compteur = Counter(tokens)

        # most_common(N) retourne les N mots les plus fréquents
        # sous forme de liste de tuples : [("vaccin",3), ("choc",1)]
        # dict() convertit ça en dictionnaire propre
        return dict(compteur.most_common(top_n))

    # ---------------------------------------------------------
    #  detecter_mots_suspects : trouve les mots alarmistes
    # ---------------------------------------------------------
    #  On compare chaque token avec notre liste de mots suspects.
    #
    #  Entrée  : ["vaccins","complot","mondial","choc","exclusif"]
    #  Sortie  : ["complot", "choc", "exclusif"]

    def detecter_mots_suspects(self, tokens):

        trouves = [mot for mot in tokens if mot in self.mots_suspects]

        # set() supprime les doublons (si le mot apparaît plusieurs fois)
        return list(set(trouves))

    # ---------------------------------------------------------
    #  detecter_sources : vérifie si le texte cite des sources
    # ---------------------------------------------------------
    #  On cherche des URLs et des formulations de citation.
    #  Retourne True si des sources sont trouvées, False sinon.

    def detecter_sources(self, texte_original):

        texte_lower = texte_original.lower()

        indicateurs = [
            "selon ", "d'après ", "source:", "sources:",
            "http://", "https://", "www.",
            "selon des chercheurs", "étude", "rapport",
            "selon l'oms", "selon l'onu", "communiqué",
        ]

        # any() retourne True dès qu'un indicateur est trouvé
        return any(ind in texte_lower for ind in indicateurs)

    # ---------------------------------------------------------
    #  analyser : méthode principale — orchestre tout le pipeline
    # ---------------------------------------------------------
    #  C'est la seule méthode appelée depuis main.py.
    #  Elle prend un Article et retourne un dict d'indicateurs.

    def analyser(self, article):

        texte_brut = article.contenu

        # --- Pipeline étape par étape ---
        texte_nettoye  = self.nettoyer(texte_brut)
        tokens         = self.tokeniser(texte_nettoye)
        tokens_filtres = self.supprimer_stop_words(tokens)

        # --- Calcul des indicateurs ---
        frequences        = self.compter_frequences(tokens_filtres)
        mots_suspects     = self.detecter_mots_suspects(tokens_filtres)
        sources_presentes = self.detecter_sources(texte_brut)

        indicateurs = {
            # Longueur totale du texte (tous les mots)
            "nb_mots": len(tokens),

            # Richesse du vocabulaire (mots uniques après filtrage)
            "nb_mots_uniques": len(set(tokens_filtres)),

            # Top 10 mots les plus fréquents
            "frequences": frequences,

            # Mots alarmistes détectés
            "mots_suspects": mots_suspects,
            "nb_mots_suspects": len(mots_suspects),

            # Présence de sources
            "sources_presentes": sources_presentes,

            # Proportion de mots suspects sur le total
            # (évite la division par zéro si texte vide)
            "ratio_suspects": (
                len(mots_suspects) / len(tokens) if len(tokens) > 0 else 0
            ),
        }

        return indicateurs