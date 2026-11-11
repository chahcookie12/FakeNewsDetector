# =============================================================
#  Classe MoteurSimilarite
#  Fichier : classes/moteur_similarite.py
# =============================================================
#
#  Ce moteur compare un article analysé à la BASE DE RÉFÉRENCE
#  d'articles étiquetés (fake / real) à l'aide de TF-IDF +
#  similarité cosinus (via scikit-learn). Il produit :
#    (a) une liste des articles de référence les plus proches,
#        avec leur étiquette et leur pourcentage de correspondance ;
#    (b) un ajustement du score de crédibilité (signal fake/real).
#
#  --- PÉRIMÈTRE DE CE FICHIER (tâche 4.1) ---
#  Cette première étape met en place UNIQUEMENT :
#    - la DÉTECTION DE DÉPENDANCE : import protégé de scikit-learn
#      (try / except ImportError) avec dégradation gracieuse ;
#    - est_disponible() : renvoie False si scikit-learn est absent
#      OU si la référence est vide, en émettant un avertissement ;
#    - le CYCLE DE VIE DU MODÈLE : construction du vectoriseur
#      TF-IDF et de la matrice de référence UNE SEULE FOIS (au
#      premier appel sur une référence non vide), puis mise en
#      cache en mémoire ; et une INVALIDATION DE CACHE à réutiliser
#      après un import du jeu de référence.
#
#  Le calcul de la similarité cosinus, la sélection / le tri des
#  correspondances et l'ajustement de score directionnel relèvent
#  des tâches suivantes (4.2, 4.5, 4.7) : ils sont seulement
#  esquissés ici pour que le module s'importe proprement.
#
#  Principe de robustesse (cohérent avec le reste du projet) :
#  l'absence de scikit-learn ou une référence vide n'interrompt
#  JAMAIS l'analyse classique (Analyseur + Score). Le moteur se
#  neutralise alors proprement (est_disponible() -> False).

# -------------------------------------------------------------
#  Import protégé de scikit-learn (dégradation gracieuse)
# -------------------------------------------------------------
#  scikit-learn est une dépendance OPTIONNELLE. Si elle n'est pas
#  installée, l'import échoue (ImportError / ModuleNotFoundError,
#  cette dernière étant une sous-classe d'ImportError). On capture
#  l'échec sans planter : un drapeau "SKLEARN_DISPONIBLE" mémorise
#  la disponibilité, et les symboles importés valent None lorsque
#  la dépendance manque.
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    # L'import a réussi : la couche de similarité est disponible.
    SKLEARN_DISPONIBLE = True
except ImportError:
    # scikit-learn absent : on neutralise proprement la couche de
    # similarité. Les références aux symboles sont mises à None pour
    # éviter toute utilisation accidentelle.
    TfidfVectorizer = None
    cosine_similarity = None

    # Drapeau consulté par est_disponible() et la construction du modèle.
    SKLEARN_DISPONIBLE = False


class MoteurSimilarite:

    # ---------------------------------------------------------
    #  Constantes de l'ajustement de score directionnel
    # ---------------------------------------------------------
    #  SEUIL_AJUSTEMENT : pourcentage minimal de la MEILLEURE
    #    correspondance pour qu'un ajustement non nul soit produit
    #    (exigences 7.4 et 7.5 : « meilleure correspondance ≥ 70 % »).
    #  AJUSTEMENT_MAX : amplitude maximale (en valeur absolue) de
    #    l'ajustement produit. On reste cohérent avec la borne
    #    [-20, +20] appliquée côté Score (tâche 6.1) : le moteur ne
    #    produit jamais une amplitude supérieure à cette borne.
    SEUIL_AJUSTEMENT = 70.0
    AJUSTEMENT_MAX = 20

    # ---------------------------------------------------------
    #  __init__ : mémorise la base de référence
    # ---------------------------------------------------------
    #  Entrée :
    #    base : une instance BaseDeDonnees (ou None si la
    #           persistance est indisponible). C'est par elle que
    #           le moteur récupère les articles de référence via
    #           recuperer_articles_reference() et détecte une
    #           référence vide via compter_articles_reference().
    #
    #  Le modèle TF-IDF n'est PAS construit ici : il est construit
    #  paresseusement (lazy) au premier besoin, puis mis en cache.

    def __init__(self, base):

        # Référence vers la persistance (peut être None : dégradation).
        self.base = base

        # --- Cache du modèle TF-IDF (artefacts en mémoire) ---
        # Ces trois attributs forment le modèle mis en cache. Ils
        # restent à None tant que le modèle n'a pas été construit.
        #   _vectoriseur     : le TfidfVectorizer ajusté sur la référence ;
        #   _matrice_reference : la matrice TF-IDF des articles de référence ;
        #   _articles_reference : la liste alignée des articles de référence
        #                         (titre, contenu, label, source) servant à
        #                         retrouver étiquette et titre par ligne.
        self._vectoriseur = None
        self._matrice_reference = None
        self._articles_reference = None

        # Drapeau indiquant si le modèle est actuellement en cache.
        # On l'utilise pour ne (re)construire le modèle qu'une seule
        # fois tant que le cache n'a pas été invalidé.
        self._modele_construit = False

        # Pour éviter d'inonder la console, l'avertissement
        # d'indisponibilité de scikit-learn n'est émis qu'une fois.
        self._avertissement_sklearn_emis = False

    # ---------------------------------------------------------
    #  _avertir : émet un avertissement de dégradation gracieuse
    # ---------------------------------------------------------
    #  On reprend la convention d'affichage du projet ("[!] ...").
    #  L'échec d'affichage ne doit jamais interrompre le programme.

    def _avertir(self, message):
        try:
            print(f"[!] {message}")
        except Exception:
            # Un échec d'affichage est sans conséquence sur l'analyse.
            pass

    # ---------------------------------------------------------
    #  _reference_est_vide : True si la référence ne contient rien
    # ---------------------------------------------------------
    #  Retourne True lorsque la comparaison est impossible faute
    #  d'articles de référence : base absente (None) ou comptage à 0.
    #  Toute erreur de lecture de la base est traitée comme une
    #  référence vide (dégradation gracieuse, jamais d'interruption).

    def _reference_est_vide(self):

        # Aucune persistance : pas de référence exploitable.
        if self.base is None:
            return True

        try:
            return self.base.compter_articles_reference() == 0
        except Exception:
            # En cas d'erreur de lecture, on se neutralise proprement.
            return True

    # ---------------------------------------------------------
    #  est_disponible : la comparaison peut-elle être effectuée ?
    # ---------------------------------------------------------
    #  La comparaison par similarité n'est possible QUE si :
    #    - scikit-learn est installé (dépendance présente) ; ET
    #    - la base de référence n'est pas vide.
    #
    #  Sinon, on renvoie False et on émet un avertissement signalant
    #  l'indisponibilité (exigences 9.1 et 9.2). L'avertissement lié
    #  à l'absence de scikit-learn n'est émis qu'une seule fois pour
    #  ne pas saturer l'affichage à chaque analyse.

    def est_disponible(self):
        """Indique si la comparaison par similarité peut être réalisée.

        Renvoie ``False`` (avec avertissement) lorsque scikit-learn est
        absent ou que la base de référence est vide ; ``True`` sinon.
        """

        # --- Dépendance scikit-learn absente (exigence 9.1) ---
        if not SKLEARN_DISPONIBLE:
            if not self._avertissement_sklearn_emis:
                self._avertir(
                    "scikit-learn n'est pas installé : la comparaison par "
                    "similarité est indisponible. L'analyse textuelle de base "
                    "se poursuit normalement."
                )
                self._avertissement_sklearn_emis = True
            return False

        # --- Référence vide (exigence 9.2) ---
        if self._reference_est_vide():
            self._avertir(
                "La base de référence est vide : la comparaison par "
                "similarité est indisponible. Importez d'abord le jeu de "
                "référence."
            )
            return False

        # Dépendance présente ET référence non vide : comparaison possible.
        return True

    # ---------------------------------------------------------
    #  _construire_modele : construit le modèle TF-IDF (une fois)
    # ---------------------------------------------------------
    #  Construit le vectoriseur TF-IDF et la matrice de référence à
    #  partir des articles de référence, puis les met en cache
    #  (exigence 5.1). La construction n'a lieu QU'UNE SEULE FOIS :
    #  si le modèle est déjà en cache, on réutilise l'existant sans
    #  le reconstruire (exigence 5.2).
    #
    #  Pré-conditions : appelée uniquement lorsque scikit-learn est
    #  présent et la référence non vide (voir est_disponible).
    #
    #  Effet de bord : renseigne _vectoriseur, _matrice_reference,
    #  _articles_reference et positionne _modele_construit à True.

    def _construire_modele(self):

        # Réutilisation du cache : on ne reconstruit jamais un modèle
        # déjà disponible (exigence 5.2).
        if self._modele_construit:
            return

        # Récupération des articles de référence depuis la persistance.
        # On conserve la liste alignée pour pouvoir retrouver, par ligne
        # de la matrice, le titre et l'étiquette correspondants.
        articles = self.base.recuperer_articles_reference()

        # Le corpus est la liste des contenus de référence, dans l'ordre
        # de la liste d'articles (donc aligné avec la matrice TF-IDF).
        corpus = [article["contenu"] for article in articles]

        # Ajustement du vectoriseur sur le corpus de référence, puis
        # calcul de la matrice TF-IDF de l'ensemble de la référence.
        # Ces deux artefacts sont calculés UNE SEULE FOIS et mis en cache.
        vectoriseur = TfidfVectorizer()
        matrice = vectoriseur.fit_transform(corpus)

        # Mise en cache des artefacts du modèle.
        self._vectoriseur = vectoriseur
        self._matrice_reference = matrice
        self._articles_reference = articles
        self._modele_construit = True

    # ---------------------------------------------------------
    #  _extraire_texte : texte comparable d'un article entrant
    # ---------------------------------------------------------
    #  L'article entrant peut être un objet Article (attributs
    #  "titre" et "contenu") ou une simple chaîne de caractères.
    #  Pour rester cohérent avec le contenu de référence (titre +
    #  corps combinés, séparés par un saut de ligne — voir l'import),
    #  on combine ici le titre puis le contenu de l'article entrant
    #  dans le même ordre, en n'utilisant que les champs non vides.
    #
    #  Entrée : article (objet Article ou str).
    #  Sortie : la chaîne de texte à vectoriser (éventuellement vide).

    def _extraire_texte(self, article):

        # Cas d'une simple chaîne : on la prend telle quelle.
        if isinstance(article, str):
            return article

        # Cas d'un objet Article : on lit titre et contenu de façon
        # défensive (attribut potentiellement absent ou None).
        titre = getattr(article, "titre", "") or ""
        contenu = getattr(article, "contenu", "") or ""

        # On ne conserve que les champs réellement renseignés
        # (non vides après nettoyage des espaces), puis on les
        # combine dans l'ordre titre puis contenu.
        parties = [partie for partie in (titre, contenu) if partie.strip()]
        return "\n".join(parties)

    # ---------------------------------------------------------
    #  _pourcentage_borne : similarité cosinus -> pourcentage [0,100]
    # ---------------------------------------------------------
    #  Convertit une similarité cosinus (théoriquement dans [0, 1]
    #  pour des vecteurs TF-IDF positifs) en pourcentage de
    #  correspondance par multiplication par 100, puis la ramène
    #  (clamp) dans l'intervalle fermé [0, 100] (exigence 5.5) :
    #    - toute valeur < 0 est ramenée à 0 ;
    #    - toute valeur > 100 (imprécision en virgule flottante)
    #      est ramenée à 100.

    def _pourcentage_borne(self, similarite):

        pourcentage = float(similarite) * 100.0

        # Clamp bas : aucune correspondance négative.
        if pourcentage < 0.0:
            return 0.0

        # Clamp haut : on absorbe les dépassements dus aux arrondis
        # en virgule flottante (par ex. 100.00000001).
        if pourcentage > 100.0:
            return 100.0

        return pourcentage

    # ---------------------------------------------------------
    #  _calculer_pourcentages : cœur de la comparaison cosinus
    # ---------------------------------------------------------
    #  Vectorise l'article entrant à l'aide du vectoriseur TF-IDF
    #  DÉJÀ ajusté sur la référence (transform, jamais fit : on
    #  réutilise le modèle en cache, exigences 5.2 et 5.3), puis
    #  calcule sa similarité cosinus avec CHAQUE article de
    #  référence (matrice en cache). Chaque similarité est convertie
    #  en pourcentage borné [0, 100] (exigence 5.5).
    #
    #  Cas du VECTEUR TF-IDF NUL (exigence 9.5) : si le texte de
    #  l'article entrant est vide, trop court, ou ne contient aucun
    #  terme du vocabulaire de référence, sa représentation TF-IDF
    #  est nulle (aucune composante non nulle). La similarité cosinus
    #  n'est alors pas pertinente : on signale l'ABSENCE de
    #  correspondance en renvoyant une liste vide (le calcul de
    #  l'ajustement, tâche 4.7, en déduira ajustement_score = 0).
    #
    #  Pré-condition : appelée uniquement lorsque la comparaison est
    #  possible (scikit-learn présent et référence non vide) ; le
    #  modèle est construit si besoin via _construire_modele().
    #
    #  Sortie : liste de pourcentages (float) ALIGNÉE, ligne par
    #  ligne, avec self._articles_reference ; liste vide si le
    #  vecteur TF-IDF de l'article entrant est nul.
    #
    #  NOTE DE PÉRIMÈTRE (tâche 4.2) : cette méthode calcule
    #  uniquement les pourcentages par référence. La sélection / le
    #  tri des meilleures correspondances (tâche 4.5) et l'ajustement
    #  de score directionnel (tâche 4.7) sont traités ailleurs.

    def _calculer_pourcentages(self, article):

        # Construction paresseuse du modèle si ce n'est pas déjà fait
        # (réutilise le cache existant, sans reconstruction inutile).
        self._construire_modele()

        # Texte comparable de l'article entrant (titre + contenu).
        texte = self._extraire_texte(article)

        # Vectorisation de l'article entrant avec le vectoriseur en
        # cache : on utilise transform (et NON fit_transform) afin de
        # projeter l'article dans le vocabulaire de la référence.
        vecteur = self._vectoriseur.transform([texte])

        # Vecteur TF-IDF nul : aucune composante non nulle. Cela
        # signifie qu'aucun terme du vocabulaire de référence n'est
        # présent (texte vide / trop court / hors vocabulaire). On
        # renvoie une liste vide : aucune correspondance (exigence 9.5).
        if vecteur.nnz == 0:
            return []

        # Similarité cosinus entre l'article entrant et l'ensemble de
        # la référence : cosine_similarity renvoie une matrice 1 x N,
        # dont on extrait la première (et unique) ligne.
        similarites = cosine_similarity(vecteur, self._matrice_reference)[0]

        # Conversion de chaque similarité en pourcentage borné [0, 100],
        # en conservant l'alignement avec self._articles_reference.
        return [self._pourcentage_borne(similarite) for similarite in similarites]

    # ---------------------------------------------------------
    #  _calculer_ajustement : ajustement de score DIRECTIONNEL
    # ---------------------------------------------------------
    #  Calcule l'ajustement de score borné à partir des N meilleures
    #  correspondances DÉJÀ sélectionnées et triées (pourcentage
    #  décroissant). La logique directionnelle (exigences 7.4 et 7.5) :
    #
    #    - On ne produit un ajustement NON NUL que si la MEILLEURE
    #      correspondance (la première de la liste triée) atteint au
    #      moins SEUIL_AJUSTEMENT (70 %). En dessous de ce seuil, la
    #      ressemblance n'est pas assez forte : ajustement = 0.
    #
    #    - Au-delà du seuil, on regarde l'étiquette MAJORITAIRE parmi
    #      les N meilleures correspondances :
    #        * majorité « fake »  -> MALUS : ajustement ≤ 0 ;
    #        * majorité « real »  -> BONUS : ajustement ≥ 0 ;
    #        * ÉGALITÉ parfaite fake/real -> aucune direction nette,
    #          ajustement neutre (0).
    #
    #  Amplitude : l'ajustement est proportionnel au pourcentage de la
    #  meilleure correspondance, gradué de 0 (à 70 %) jusqu'à
    #  AJUSTEMENT_MAX (à 100 %), puis arrondi à l'entier le plus proche.
    #  Le résultat est borné dans [-AJUSTEMENT_MAX, +AJUSTEMENT_MAX] :
    #  négatif pour une majorité « fake », positif pour « real ».
    #
    #  Entrée : correspondances, liste de dict {titre, label,
    #           pourcentage} triée par pourcentage décroissant.
    #  Sortie : un entier borné (l'ajustement de score).

    def _calculer_ajustement(self, correspondances):

        # Aucune correspondance : aucun signal, ajustement neutre.
        if not correspondances:
            return 0

        # La meilleure correspondance est la première (liste triée par
        # pourcentage décroissant). En deçà du seuil de 70 %, on
        # n'ajuste pas (exigences 7.4 et 7.5 : « ≥ 70 % »).
        meilleur_pourcentage = correspondances[0]["pourcentage"]
        if meilleur_pourcentage < self.SEUIL_AJUSTEMENT:
            return 0

        # Étiquette majoritaire parmi les N meilleures correspondances.
        nb_fake = sum(1 for c in correspondances if c["label"] == "fake")
        nb_real = sum(1 for c in correspondances if c["label"] == "real")

        # Égalité parfaite : aucune direction dominante, on reste neutre.
        if nb_fake == nb_real:
            return 0

        # Amplitude proportionnelle : 0 au seuil (70 %), AJUSTEMENT_MAX
        # à 100 %. On normalise le pourcentage dans [seuil, 100] sur
        # [0, 1], puis on multiplie par l'amplitude maximale.
        proportion = (meilleur_pourcentage - self.SEUIL_AJUSTEMENT) / (
            100.0 - self.SEUIL_AJUSTEMENT
        )
        amplitude = round(proportion * self.AJUSTEMENT_MAX)

        # Direction selon l'étiquette majoritaire :
        #   fake -> malus (négatif) ; real -> bonus (positif).
        if nb_fake > nb_real:
            return -amplitude
        return amplitude

    # ---------------------------------------------------------
    #  comparer : point d'entrée public de la comparaison
    # ---------------------------------------------------------
    #  Compare l'article entrant à la base de référence et construit
    #  le Resultat_Similarite consommé par l'affichage et par Score.
    #
    #  Représentation du Resultat_Similarite (cf. design, modèle 2) :
    #  un dictionnaire simple, cohérent avec le reste du projet où
    #  les articles de référence sont déjà manipulés sous forme de
    #  dict ({id, titre, contenu, label, source}) :
    #
    #      {
    #          "disponible": bool,
    #          "correspondances": [ {titre, label, pourcentage}, ... ],
    #          "ajustement_score": int,
    #      }
    #
    #  Règles couvertes par cette méthode :
    #    - INDISPONIBILITÉ (dépendance absente ou référence vide) :
    #      renvoie disponible=False, correspondances=[],
    #      ajustement_score=0 (exigences 9.1, 9.2 — déléguées à
    #      est_disponible()).
    #    - SÉLECTION : au plus min(5, nombre de correspondances)
    #      meilleures correspondances (exigence 6.1).
    #    - TRI : pourcentage décroissant, puis, à égalité, titre
    #      alphabétique croissant — ordre DÉTERMINISTE (exigence 6.2).
    #    - RÉSULTAT : disponible=True + liste ordonnée (≤ 5) +
    #      ajustement_score (exigence 6.3).
    #    - AUCUNE CORRESPONDANCE PERTINENTE : liste vide, sans erreur
    #      (exigence 6.4 ; couvre aussi le vecteur TF-IDF nul de
    #      l'exigence 9.5, _calculer_pourcentages renvoyant []).
    #
    #  AJUSTEMENT DIRECTIONNEL (tâche 4.7) : ajustement_score est
    #  calculé via _calculer_ajustement() à partir du seuil de 70 % sur
    #  la meilleure correspondance et de l'étiquette majoritaire fake/
    #  real des N meilleures correspondances (exigences 7.4, 7.5).
    #
    #  Entrée : article (objet Article ou str).
    #  Sortie : le Resultat_Similarite (dict) décrit ci-dessus.

    def comparer(self, article):
        """Compare ``article`` à la référence et renvoie un Resultat_Similarite.

        Renvoie un dictionnaire ``{disponible, correspondances,
        ajustement_score}``. Lorsque la comparaison est indisponible
        (scikit-learn absent ou référence vide), ``disponible`` vaut
        ``False``, ``correspondances`` est vide et ``ajustement_score``
        vaut 0.
        """

        # --- Indisponibilité : dégradation gracieuse ---
        # est_disponible() couvre l'absence de scikit-learn (9.1) et la
        # référence vide (9.2). On renvoie alors un résultat neutre.
        if not self.est_disponible():
            return {
                "disponible": False,
                "correspondances": [],
                "ajustement_score": 0,
            }

        # --- Calcul des pourcentages par référence (tâche 4.2) ---
        # Liste de pourcentages [0, 100] ALIGNÉE avec
        # self._articles_reference. Liste vide si le vecteur TF-IDF de
        # l'article entrant est nul (texte vide / hors vocabulaire).
        pourcentages = self._calculer_pourcentages(article)

        # --- Aucune correspondance pertinente (exigences 6.4, 9.5) ---
        # Vecteur nul : on renvoie une liste vide sans signaler d'erreur.
        if not pourcentages:
            return {
                "disponible": True,
                "correspondances": [],
                "ajustement_score": 0,
            }

        # --- Construction des correspondances candidates ---
        # On apparie chaque pourcentage avec le titre et l'étiquette de
        # l'article de référence situé sur la même ligne (alignement
        # garanti par _calculer_pourcentages et _construire_modele).
        correspondances = [
            {
                "titre": reference["titre"],
                "label": reference["label"],
                "pourcentage": pourcentage,
            }
            for reference, pourcentage in zip(
                self._articles_reference, pourcentages
            )
        ]

        # --- Tri déterministe (exigence 6.2) ---
        # Clé de tri : pourcentage DÉCROISSANT, puis titre alphabétique
        # CROISSANT à pourcentages égaux. On obtient un ordre stable et
        # identique d'une exécution à l'autre. Le tri de Python étant
        # stable, on trie d'abord par titre croissant (clé secondaire),
        # puis par pourcentage décroissant (clé primaire).
        correspondances.sort(key=lambda c: c["titre"])
        correspondances.sort(key=lambda c: c["pourcentage"], reverse=True)

        # --- Sélection des meilleures correspondances (exigence 6.1) ---
        # On retient au plus min(5, nombre de correspondances) entrées.
        meilleures = correspondances[: min(5, len(correspondances))]

        # --- Ajustement de score directionnel (tâche 4.7) ---
        # Calcul borné selon le seuil de 70 % sur la meilleure
        # correspondance et l'étiquette majoritaire (fake/real) des N
        # meilleures correspondances (exigences 7.4, 7.5) : majorité
        # « fake » -> ajustement ≤ 0 ; majorité « real » -> ajustement
        # ≥ 0 ; en deçà du seuil ou à égalité, ajustement neutre (0).
        ajustement_score = self._calculer_ajustement(meilleures)

        # --- Resultat_Similarite (exigence 6.3) ---
        return {
            "disponible": True,
            "correspondances": meilleures,
            "ajustement_score": ajustement_score,
        }

    # ---------------------------------------------------------
    #  invalider_cache : force la reconstruction au prochain appel
    # ---------------------------------------------------------
    #  À appeler APRÈS un import du jeu de référence (exigence 5.4) :
    #  le cache du modèle TF-IDF est vidé, de sorte que la prochaine
    #  comparaison reconstruise le vectoriseur et la matrice de
    #  référence à partir des articles désormais présents en base.

    def invalider_cache(self):
        """Invalide le cache du modèle TF-IDF (à appeler après un import).

        Vide le vectoriseur, la matrice de référence et la liste alignée
        des articles afin que la prochaine comparaison reconstruise le
        modèle à partir de la référence à jour.
        """

        self._vectoriseur = None
        self._matrice_reference = None
        self._articles_reference = None
        self._modele_construit = False
