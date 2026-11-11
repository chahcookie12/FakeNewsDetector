
from classes.article import Article
from classes.analyseur import Analyseur
from classes.score import Score

from classes.base_donnees import BaseDeDonnees, ErreurBaseDeDonnees
from classes.importateur_dataset import ImportateurDataset
from classes.moteur_similarite import MoteurSimilarite


def separateur():
    print("─" * 50)


def _etiquette_dominante(correspondances):
    """Renvoie l'étiquette majoritaire ("fake"/"real") des correspondances.

    On compte les étiquettes des correspondances fournies et on retourne
    celle qui domine. En cas d'égalité parfaite (ou de liste vide), on
    renvoie None : aucune direction nette. Cette information sert
    uniquement à composer la ligne explicative du Score (exigence 7.6).
    """

    nb_fake = sum(1 for c in correspondances if c["label"] == "fake")
    nb_real = sum(1 for c in correspondances if c["label"] == "real")

    if nb_fake > nb_real:
        return "fake"
    if nb_real > nb_fake:
        return "real"
    return None


def _afficher_correspondances(resultat_similarite):
    """Affiche les articles de référence les plus proches.

    Le paramètre est le Resultat_Similarite renvoyé par
    MoteurSimilarite.comparer : un dict {disponible, correspondances,
    ajustement_score}. Trois situations (exigences 8.1 à 8.4) :

      1. disponible=False : message d'indisponibilité, SANS liste.
      2. disponible=True mais aucune correspondance : message dédié
         indiquant l'absence d'article de référence proche.
      3. disponible=True avec correspondances : on affiche, dans
         l'ordre fourni par le moteur, le titre, l'étiquette et le
         pourcentage arrondi à l'entier le plus proche et borné [0, 100].
    """

    separateur()
    print("  ARTICLES DE RÉFÉRENCE LES PLUS PROCHES")
    separateur()

    # --- Comparaison indisponible (exigence 8.4) ---
    # On signale l'indisponibilité sans afficher de liste.
    if not resultat_similarite["disponible"]:
        print("[i] Comparaison par similarité indisponible "
              "(scikit-learn absent ou base de référence vide).\n")
        return

    correspondances = resultat_similarite["correspondances"]

    # --- Aucune correspondance pertinente (exigence 8.3) ---
    if not correspondances:
        print("Aucun article de référence proche n'a été trouvé.\n")
        return

    # --- Affichage des correspondances dans l'ordre fourni (8.1, 8.2) ---
    for correspondance in correspondances:
        # Pourcentage arrondi à l'entier le plus proche puis borné
        # [0, 100] (exigence 8.1). Le moteur borne déjà la valeur, mais
        # on reborne par sécurité après arrondi.
        pourcentage = max(0, min(100, round(correspondance["pourcentage"])))
        etiquette = str(correspondance["label"]).upper()
        print(f"  • [{etiquette}] {correspondance['titre']} "
              f"— {pourcentage}% de correspondance")

    print()


def analyser_texte(analyseur, scoreur, base, moteur=None):
    """Demande un texte à l'utilisateur et affiche le résultat.

    Le paramètre "base" est l'instance BaseDeDonnees (ou None si la
    persistance n'est pas disponible). Le paramètre "moteur" est
    l'instance MoteurSimilarite (ou None lorsque la couche de similarité
    n'est pas branchée). Après l'affichage du résultat, l'analyse est
    sauvegardée AUTOMATIQUEMENT, sans action manuelle de l'utilisateur.
    """

    separateur()
    print("  ANALYSE D'UN TEXTE")
    separateur()

    # --- Saisie du titre ---
    titre = input("Titre de l'article (ou Entrée pour passer) : ").strip()
    if not titre:
        titre = "Sans titre"

    # --- Saisie du contenu ---
    print("\nCollez votre texte ci-dessous.")
    print("Appuyez sur Entrée deux fois pour terminer.\n")

    lignes = []
    while True:
        ligne = input()
        if ligne == "":
            # Deuxième Entrée consécutive = fin de saisie
            if lignes and lignes[-1] == "":
                break
        lignes.append(ligne)

    contenu = "\n".join(lignes).strip()

    if not contenu:
        print("\n[!] Texte vide — analyse annulée.\n")
        return

    # --- Saisie optionnelle de la source ---
    source = input("\nSource (site, journal... ou Entrée pour passer) : ").strip()
    if not source:
        source = None

    # --- Création de l'Article ---
    article = Article(titre=titre, contenu=contenu, source=source)

    # --- Analyse + Scoring ---
    print("\nAnalyse en cours...")
    indicateurs = analyseur.analyser(article)

    # --- Comparaison par similarité (dégradation gracieuse) ---
    #
    #  Le MoteurSimilarite est OPTIONNEL : s'il n'est pas branché
    #  (moteur is None), on conserve le comportement historique (aucun
    #  ajustement, aucun affichage de correspondances).
    #
    #  Quand il est présent, on capture TOUTE erreur du moteur
    #  (exigence 10.3) : la comparaison ne doit jamais interrompre
    #  l'analyse textuelle de base. En cas d'échec (ou si scikit-learn
    #  est absent / référence vide), on retombe sur un résultat
    #  « indisponible » neutre (ajustement_score = 0) et l'analyse de
    #  base se poursuit normalement (exigences 9.6, 10.3).
    resultat_similarite = {
        "disponible": False,
        "correspondances": [],
        "ajustement_score": 0,
    }
    if moteur is not None:
        try:
            resultat_similarite = moteur.comparer(article)
        except Exception:
            # Toute erreur du moteur est absorbée : on signale
            # l'indisponibilité sans interrompre le programme.
            resultat_similarite = {
                "disponible": False,
                "correspondances": [],
                "ajustement_score": 0,
            }

    # Étiquette dominante et meilleure correspondance servent à composer
    # la ligne explicative du Score (exigence 7.6). meilleur_pourcentage
    # est celui de la première correspondance (liste triée décroissante).
    correspondances = resultat_similarite["correspondances"]
    etiquette_dominante = _etiquette_dominante(correspondances)
    meilleur_pourcentage = (
        correspondances[0]["pourcentage"] if correspondances else None
    )

    # Le score intègre l'ajustement de similarité (0 si indisponible :
    # le score est alors identique à l'analyse textuelle seule).
    resultat = scoreur.calculer(
        indicateurs,
        ajustement_score=resultat_similarite["ajustement_score"],
        etiquette_dominante=etiquette_dominante,
        meilleur_pourcentage=meilleur_pourcentage,
    )

    # --- Affichage du résultat ---
    scoreur.afficher(resultat)

    # --- Affichage des articles de référence similaires ---
    # On présente les correspondances (ou un message dédié) seulement
    # lorsque la couche de similarité est branchée.
    if moteur is not None:
        _afficher_correspondances(resultat_similarite)

    # --- Résumé des indicateurs ---
    print("  Indicateurs extraits :")
    print(f"    Nombre de mots      : {indicateurs['nb_mots']}")
    print(f"    Mots uniques        : {indicateurs['nb_mots_uniques']}")
    print(f"    Sources détectées   : {'Oui ✓' if indicateurs['sources_presentes'] else 'Non ✗'}")
    print(f"    Mots suspects       : {indicateurs['mots_suspects'] or 'aucun'}")
    if indicateurs['frequences']:
        top = list(indicateurs['frequences'].items())[:5]
        top_str = ", ".join(f"{m}({n})" for m, n in top)
        print(f"    Top 5 mots          : {top_str}")
    separateur()

    # --- Sauvegarde automatique de l'analyse ---
    #
    #  Une fois le résultat affiché, on enregistre l'analyse SANS
    #  demander à l'utilisateur. Trois situations possibles :
    #
    #    1. Pas de persistance disponible (base is None) : on prévient
    #       et on continue, le résultat reste affiché.
    #    2. Enregistrement réussi : on confirme avec l'identifiant créé.
    #       Si même l'affichage de cette confirmation échoue, on poursuit
    #       sans l'afficher.
    #    3. Enregistrement échoué (ErreurBaseDeDonnees) : on signale que
    #       la sauvegarde a échoué, mais le programme continue et le
    #       résultat reste affiché.

    if base is None:
        # Persistance indisponible : l'analyse reste utilisable.
        print("[!] Persistance indisponible — analyse non enregistrée.\n")
        return

    try:
        identifiant = base.enregistrer_analyse(article, resultat)
        # Succès : on tente d'afficher une confirmation lisible.
        # Si l'affichage lui-même échoue, on poursuit sans confirmation.
        try:
            print(f"[✓] Analyse enregistrée (#{identifiant}).\n")
        except Exception:
            # L'échec d'affichage ne doit pas interrompre le programme.
            pass
    except ErreurBaseDeDonnees as e:
        # Échec d'enregistrement : on prévient et on continue.
        # Le résultat de l'analyse a déjà été affiché plus haut.
        print(f"[!] Sauvegarde échouée : {e}\n")


def afficher_historique(base):
    """Affiche l'historique des analyses enregistrées.

    Le paramètre "base" est l'instance BaseDeDonnees (ou None si la
    persistance n'est pas disponible). Chaque analyse est affichée avec
    son titre, son score, son verdict et sa date.
    """

    separateur()
    print("  HISTORIQUE DES ANALYSES")
    separateur()

    # Pas de persistance : rien à afficher, on prévient et on revient.
    if base is None:
        print("[!] Persistance indisponible — historique inaccessible.\n")
        return

    # Récupération de l'historique. En cas d'erreur de lecture, on
    # affiche un message lisible et on poursuit l'exécution du programme.
    try:
        historique = base.recuperer_historique()
    except ErreurBaseDeDonnees as e:
        print(f"[!] Impossible de lire l'historique : {e}\n")
        return

    # Historique vide : message dédié.
    if not historique:
        print("L'historique est vide — aucune analyse enregistrée pour l'instant.\n")
        return

    # Affichage de chaque analyse (titre, score, verdict, date).
    for analyse in historique:
        print(f"  #{analyse['id']}  {analyse['date']}")
        print(f"    Titre   : {analyse['titre']}")
        print(f"    Score   : {analyse['score']}/100")
        print(f"    Verdict : {analyse['verdict']}")
        separateur()

    print()


def importer_reference(base, moteur):
    """Importe le jeu de référence (CSV) dans la base de référence.

    Le paramètre "base" est l'instance BaseDeDonnees (ou None si la
    persistance n'est pas disponible) et "moteur" l'instance
    MoteurSimilarite dont le cache doit être invalidé après un import
    réussi (exigence 5.4).

    Trois situations :
      1. Persistance indisponible (base is None) : on prévient et on
         revient sans planter (exigence cohérente avec base=None).
      2. Import effectué : on affiche le message de synthèse du rapport.
         Si au moins un article a été importé, on invalide le cache du
         moteur pour que la prochaine comparaison reconstruise le modèle.
      3. Rien à importer (dossier absent, aucun CSV reconnu) : le rapport
         contient un message explicatif que l'on affiche tel quel.
    """

    separateur()
    print("  IMPORT DU JEU DE RÉFÉRENCE")
    separateur()

    # Pas de persistance : impossible d'importer, on prévient et on sort.
    if base is None:
        print("[!] Persistance indisponible — import impossible.\n")
        return

    # Lancement de l'import par lot. L'ImportateurDataset gère lui-même
    # la dégradation gracieuse (dossier introuvable, CSV manquants...)
    # et retourne toujours un rapport avec un message lisible.
    print("Import en cours... (cela peut prendre un moment pour un gros "
          "jeu de données)\n")
    importateur = ImportateurDataset(base)
    rapport = importateur.importer()

    # Affichage de la synthèse de l'import.
    print(rapport["message"])
    print()

    # Après un import ayant ajouté des articles, on invalide le cache du
    # moteur de similarité afin que la prochaine comparaison reconstruise
    # le vectoriseur et la matrice de référence (exigence 5.4).
    if moteur is not None and rapport["total_importes"] > 0:
        moteur.invalider_cache()


def main():

    # Initialisation — fait une seule fois au démarrage
    analyseur = Analyseur()
    scoreur   = Score()

    # --- Initialisation de la persistance (dégradation gracieuse) ---
    #
    #  On tente d'ouvrir la base de données. Si l'initialisation
    #  échoue (connexion impossible, dossier non créable, schéma...),
    #  on affiche un avertissement et on continue SANS persistance :
    #  la base reste à None et l'analyse demeure pleinement utilisable.
    try:
        base = BaseDeDonnees()
    except ErreurBaseDeDonnees as e:
        base = None
        print(f"\n[!] Base de données indisponible : {e}")
        print("    Le programme continue sans persistance "
              "(les analyses ne seront pas enregistrées).")

    # --- Initialisation du moteur de similarité ---
    #
    #  Une SEULE instance de MoteurSimilarite est créée pour toute la
    #  session : le modèle TF-IDF est ainsi construit une fois puis mis
    #  en cache. Le moteur accepte base=None et se neutralise proprement
    #  (est_disponible() -> False) si scikit-learn est absent ou si la
    #  référence est vide, sans jamais interrompre l'analyse de base.
    moteur = MoteurSimilarite(base)

    print("\n" + "═" * 50)
    print("   FAKE NEWS DETECTOR — ENSIAS PFA 2025")
    print("═" * 50)

    while True:
        print("\nQue voulez-vous faire ?")
        print("  1. Analyser un texte")
        print("  2. Afficher l'historique")
        print("  3. Importer le jeu de référence")
        print("  0. Quitter")
        print()

        choix = input("Votre choix : ").strip()

        if choix == "1":
            analyser_texte(analyseur, scoreur, base, moteur)

        elif choix == "2":
            afficher_historique(base)

        elif choix == "3":
            importer_reference(base, moteur)

        elif choix == "0":
            # On ferme proprement la connexion à la base avant de quitter
            # (uniquement si la persistance était disponible).
            if base is not None:
                base.fermer()
            print("\nAu revoir !\n")
            break

        else:
            print("\n[!] Choix invalide. Tapez 1, 2, 3 ou 0.\n")


# Ce bloc garantit que main() ne s'exécute que si on lance
# ce fichier directement (python main.py) et pas si on
# l'importe depuis un autre fichier.
if __name__ == "__main__":
    main()
