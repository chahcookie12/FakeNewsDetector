# =============================================================
#  Classe Score
#  Fichier : classes/score.py
# =============================================================
#
#  Reçoit les indicateurs calculés par Analyseur et produit :
#    - un score numérique entre 0 et 100
#    - un verdict : FAKE / DOUTEUX / FIABLE
#    - un détail des points attribués (pour expliquer le résultat)
#
#  Logique générale :
#    On part d'un score de BASE (50 — neutre, "on ne sait pas").
#    Ensuite chaque indicateur ajoute ou retire des points.
#    À la fin on bloque le résultat entre 0 et 100 avec clamp().
#
#    Score final = 50 + bonus - malus


class Score:

    # ---------------------------------------------------------
    #  Constantes de scoring
    # ---------------------------------------------------------
    #  On regroupe tous les chiffres ici plutôt que de les
    #  disperser dans le code. Avantage : si on veut ajuster
    #  la pondération, on touche à un seul endroit.

    SCORE_BASE        = 50   # point de départ neutre

    # Bonus (points ajoutés)
    BONUS_SOURCES     = 20   # le texte cite des sources fiables
    BONUS_TEXTE_LONG  = 10   # texte long = probablement plus élaboré
    BONUS_VOCABULAIRE = 10   # vocabulaire riche = style journalistique

    # Malus (points retirés) — par mot suspect trouvé
    MALUS_PAR_MOT_SUSPECT = 8

    # Malus supplémentaire si le texte est TRÈS court
    MALUS_TEXTE_TRES_COURT = 15

    # Malus si le ratio suspects est élevé (plus de 15% des mots)
    MALUS_RATIO_ELEVE = 10

    # Seuils pour les bonus/malus de longueur
    SEUIL_TEXTE_LONG       = 100   # nb de mots pour être "long"
    SEUIL_TEXTE_TRES_COURT = 20    # nb de mots pour être "très court"
    SEUIL_VOCABULAIRE      = 30    # nb de mots uniques pour "riche"
    SEUIL_RATIO_ELEVE      = 0.15  # 15% de mots suspects = alarmant

    # Seuils de classification
    SEUIL_FAKE    = 40
    SEUIL_DOUTEUX = 70

    # ---------------------------------------------------------
    #  calculer : produit le score à partir des indicateurs
    # ---------------------------------------------------------
    #  Entrée  : le dictionnaire retourné par Analyseur.analyser()
    #  Sortie  : un dictionnaire avec score, verdict et détail
    #
    #  On retourne un dict plutôt qu'un simple entier pour
    #  pouvoir expliquer le résultat à l'utilisateur.

    def calculer(self, indicateurs):

        score  = self.SCORE_BASE
        detail = []   # liste des ajustements appliqués

        # On note le point de départ dans le détail
        detail.append(f"Score de base : {self.SCORE_BASE}")

        # -------------------------------------------------
        #  RÈGLE 1 : présence de sources → BONUS
        # -------------------------------------------------
        #  Un article qui cite ses sources est plus crédible.
        #  "selon l'OMS", "https://...", "étude publiée" etc.

        if indicateurs["sources_presentes"]:
            score += self.BONUS_SOURCES
            detail.append(f"+{self.BONUS_SOURCES} sources citées ✓")
        else:
            detail.append("+0  aucune source détectée")

        # -------------------------------------------------
        #  RÈGLE 2 : mots suspects → MALUS (par mot)
        # -------------------------------------------------
        #  Chaque mot suspect (urgent, complot, choc...) retire
        #  des points. Plus il y en a, plus le malus est lourd.
        #  On plafonne à 5 mots pour éviter un score négatif
        #  à cause d'un seul critère.

        nb_suspects = indicateurs["nb_mots_suspects"]

        if nb_suspects > 0:
            # min(nb_suspects, 5) : on compte au max 5 mots suspects
            # pour ne pas écraser tous les autres critères
            nb_comptabilises = min(nb_suspects, 5)
            malus            = nb_comptabilises * self.MALUS_PAR_MOT_SUSPECT
            score           -= malus
            mots             = ", ".join(indicateurs["mots_suspects"])
            detail.append(
                f"-{malus} {nb_suspects} mot(s) suspect(s) : [{mots}]"
            )
        else:
            detail.append("+0  aucun mot suspect")

        # -------------------------------------------------
        #  RÈGLE 3 : longueur du texte → BONUS ou MALUS
        # -------------------------------------------------
        #  Un texte très court (< 20 mots) est souvent un titre
        #  sensationnaliste ou un post sans substance.
        #  Un texte long (> 100 mots) indique un article élaboré.

        nb_mots = indicateurs["nb_mots"]

        if nb_mots < self.SEUIL_TEXTE_TRES_COURT:
            score -= self.MALUS_TEXTE_TRES_COURT
            detail.append(
                f"-{self.MALUS_TEXTE_TRES_COURT} texte très court ({nb_mots} mots)"
            )
        elif nb_mots >= self.SEUIL_TEXTE_LONG:
            score += self.BONUS_TEXTE_LONG
            detail.append(
                f"+{self.BONUS_TEXTE_LONG} texte long ({nb_mots} mots) ✓"
            )
        else:
            detail.append(f"+0  longueur moyenne ({nb_mots} mots)")

        # -------------------------------------------------
        #  RÈGLE 4 : richesse du vocabulaire → BONUS
        # -------------------------------------------------
        #  Un vocabulaire varié (beaucoup de mots différents)
        #  est caractéristique d'un style journalistique sérieux.
        #  Un texte répétitif avec peu de mots distincts est suspect.

        nb_uniques = indicateurs["nb_mots_uniques"]

        if nb_uniques >= self.SEUIL_VOCABULAIRE:
            score += self.BONUS_VOCABULAIRE
            detail.append(
                f"+{self.BONUS_VOCABULAIRE} vocabulaire riche ({nb_uniques} mots uniques) ✓"
            )
        else:
            detail.append(f"+0  vocabulaire limité ({nb_uniques} mots uniques)")

        # -------------------------------------------------
        #  RÈGLE 5 : ratio de mots suspects élevé → MALUS
        # -------------------------------------------------
        #  Si plus de 15% des mots du texte sont suspects,
        #  c'est un signal fort de désinformation.
        #  Ce malus s'ajoute aux malus individuels par mot.

        ratio = indicateurs["ratio_suspects"]

        if ratio > self.SEUIL_RATIO_ELEVE:
            score -= self.MALUS_RATIO_ELEVE
            detail.append(
                f"-{self.MALUS_RATIO_ELEVE} ratio suspects élevé ({ratio:.0%} des mots)"
            )

        # -------------------------------------------------
        #  Clamp : on force le score entre 0 et 100
        # -------------------------------------------------
        #  Sans ça, on pourrait avoir -10 ou 115.
        #  max(0, score) empêche d'aller en dessous de 0.
        #  min(100, ...) empêche de dépasser 100.

        score = max(0, min(100, score))

        # -------------------------------------------------
        #  Classification finale
        # -------------------------------------------------

        verdict = self.classifier(score)

        return {
            "score":   score,
            "verdict": verdict,
            "detail":  detail,
        }

    # ---------------------------------------------------------
    #  classifier : convertit un score en verdict lisible
    # ---------------------------------------------------------
    #  Entrée  : 35
    #  Sortie  : "FAKE"

    def classifier(self, score):

        if score < self.SEUIL_FAKE:
            return "FAKE"
        elif score < self.SEUIL_DOUTEUX:
            return "DOUTEUX"
        else:
            return "FIABLE"

    # ---------------------------------------------------------
    #  afficher : affiche le résultat de façon lisible
    # ---------------------------------------------------------
    #  Reçoit le dictionnaire retourné par calculer()
    #  et l'affiche proprement dans la console.

    def afficher(self, resultat):

        # On choisit une couleur selon le verdict
        # (codes ANSI — fonctionnent dans la plupart des terminaux)
        couleurs = {
            "FAKE":    "\033[91m",   # rouge
            "DOUTEUX": "\033[93m",   # orange/jaune
            "FIABLE":  "\033[92m",   # vert
        }
        RESET = "\033[0m"

        verdict = resultat["verdict"]
        score   = resultat["score"]
        couleur = couleurs.get(verdict, "")

        print("\n" + "=" * 50)
        print("  RÉSULTAT DE L'ANALYSE")
        print("=" * 50)

        # Barre de progression visuelle (50 caractères de large)
        # Ex : score 72 → ████████████████████████████████████░░░░░░░░░░░░░░
        rempli  = int(score / 2)              # 0-100 → 0-50 caractères
        vide    = 50 - rempli
        barre   = "█" * rempli + "░" * vide
        print(f"  [{barre}]")
        print(f"  Score : {couleur}{score}/100{RESET}")
        print(f"  Verdict : {couleur}{'█' * 3}  {verdict}  {'█' * 3}{RESET}")

        print("\n  Détail du scoring :")
        for ligne in resultat["detail"]:
            print(f"    {ligne}")

        print("=" * 50 + "\n")