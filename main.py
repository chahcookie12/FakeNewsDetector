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


def separateur():
    print("─" * 50)


def analyser_texte(analyseur, scoreur):
    """Demande un texte à l'utilisateur et affiche le résultat."""

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


def main():

    # Initialisation — fait une seule fois au démarrage
    analyseur = Analyseur()
    scoreur   = Score()

    print("\n" + "═" * 50)
    print("   FAKE NEWS DETECTOR — ENSIAS PFA 2025")
    print("═" * 50)

    while True:
        print("\nQue voulez-vous faire ?")
        print("  1. Analyser un texte")
        print("  0. Quitter")
        print()

        choix = input("Votre choix : ").strip()

        if choix == "1":
            analyser_texte(analyseur, scoreur)

        elif choix == "0":
            print("\nAu revoir !\n")
            break

        else:
            print("\n[!] Choix invalide. Tapez 1 ou 0.\n")


# Ce bloc garantit que main() ne s'exécute que si on lance
# ce fichier directement (python main.py) et pas si on
# l'importe depuis un autre fichier.
if __name__ == "__main__":
    main()