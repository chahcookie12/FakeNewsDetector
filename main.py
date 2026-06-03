# =============================================================
#  FakeNewsDetector — main.py
#  Auteurs : Ali CHAHBOUBI & Mohammed Amine KARMOUCH
#  ENSIAS — 1ère Année Génie Logiciel
# =============================================================
#
#  Point d'entrée du programme.
#  Lance : python main.py

from classes.article import Article
from classes.analyseur import Analyseur
from classes.score import Score

# Persistance locale (SQLite). On importe la classe BaseDeDonnees
# et son exception métier ErreurBaseDeDonnees pour pouvoir
# enregistrer les analyses et consulter l'historique.
from classes.base_donnees import BaseDeDonnees, ErreurBaseDeDonnees


def separateur():
    print("─" * 50)


def analyser_texte(analyseur, scoreur, base):
    """Demande un texte à l'utilisateur et affiche le résultat.

    Le paramètre "base" est l'instance BaseDeDonnees (ou None si la
    persistance n'est pas disponible). Après l'affichage du résultat,
    l'analyse est sauvegardée AUTOMATIQUEMENT, sans action manuelle de
    l'utilisateur.
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
    resultat    = scoreur.calculer(indicateurs)

    # --- Affichage du résultat ---
    scoreur.afficher(resultat)

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

    print("\n" + "═" * 50)
    print("   FAKE NEWS DETECTOR — ENSIAS PFA 2025")
    print("═" * 50)

    while True:
        print("\nQue voulez-vous faire ?")
        print("  1. Analyser un texte")
        print("  2. Afficher l'historique")
        print("  0. Quitter")
        print()

        choix = input("Votre choix : ").strip()

        if choix == "1":
            analyser_texte(analyseur, scoreur, base)

        elif choix == "2":
            afficher_historique(base)

        elif choix == "0":
            # On ferme proprement la connexion à la base avant de quitter
            # (uniquement si la persistance était disponible).
            if base is not None:
                base.fermer()
            print("\nAu revoir !\n")
            break

        else:
            print("\n[!] Choix invalide. Tapez 1, 2 ou 0.\n")


# Ce bloc garantit que main() ne s'exécute que si on lance
# ce fichier directement (python main.py) et pas si on
# l'importe depuis un autre fichier.
if __name__ == "__main__":
    main()
