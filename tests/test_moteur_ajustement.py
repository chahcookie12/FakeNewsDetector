# =============================================================
#  test_moteur_ajustement.py
#  Tests unitaires — MoteurSimilarite : ajustement de score
#  directionnel (tâche 4.7)
# =============================================================
#
#  Ces tests couvrent UNIQUEMENT le périmètre de la tâche 4.7 :
#  le calcul DIRECTIONNEL de l'ajustement de score à partir des N
#  meilleures correspondances déjà sélectionnées/triées.
#
#  Règles vérifiées :
#    - meilleure correspondance ≥ 70 % ET majorité « fake »
#      -> ajustement ≤ 0 (malus, exigence 7.4) ;
#    - meilleure correspondance ≥ 70 % ET majorité « real »
#      -> ajustement ≥ 0 (bonus, exigence 7.5) ;
#    - meilleure correspondance < 70 % -> ajustement = 0 ;
#    - égalité parfaite fake/real -> ajustement = 0 ;
#    - indisponibilité (base=None) -> disponible=False,
#      correspondances=[], ajustement_score=0 (exigence 9.2).
#
#  Ces tests s'appuient sur la méthode pure _calculer_ajustement
#  (dicts de correspondances passés directement) : ILS NE
#  NÉCESSITENT PAS scikit-learn.

from classes.article import Article
from classes.moteur_similarite import MoteurSimilarite


def _moteur():
    """Instancie un moteur sans persistance : suffisant pour tester
    la méthode pure _calculer_ajustement."""
    return MoteurSimilarite(None)


def _correspondance(titre, label, pourcentage):
    return {"titre": titre, "label": label, "pourcentage": pourcentage}


# -------------------------------------------------------------
#  Majorité « fake » au-delà du seuil -> malus (≤ 0)
# -------------------------------------------------------------

def test_ajustement_majorite_fake_donne_malus():
    """Meilleure ≥ 70 % et majorité fake : ajustement ≤ 0 (7.4)."""
    correspondances = [
        _correspondance("A", "fake", 92.0),
        _correspondance("B", "fake", 80.0),
        _correspondance("C", "real", 75.0),
    ]
    ajustement = _moteur()._calculer_ajustement(correspondances)
    assert ajustement <= 0
    # Amplitude bornée à [-20, 0].
    assert -20 <= ajustement <= 0


# -------------------------------------------------------------
#  Majorité « real » au-delà du seuil -> bonus (≥ 0)
# -------------------------------------------------------------

def test_ajustement_majorite_real_donne_bonus():
    """Meilleure ≥ 70 % et majorité real : ajustement ≥ 0 (7.5)."""
    correspondances = [
        _correspondance("A", "real", 95.0),
        _correspondance("B", "real", 82.0),
        _correspondance("C", "fake", 71.0),
    ]
    ajustement = _moteur()._calculer_ajustement(correspondances)
    assert ajustement >= 0
    assert 0 <= ajustement <= 20


# -------------------------------------------------------------
#  Meilleure correspondance sous le seuil -> aucun ajustement
# -------------------------------------------------------------

def test_ajustement_sous_seuil_est_nul():
    """Meilleure < 70 % : aucun ajustement, quelle que soit la
    majorité d'étiquettes."""
    correspondances = [
        _correspondance("A", "fake", 69.9),
        _correspondance("B", "fake", 60.0),
        _correspondance("C", "fake", 50.0),
    ]
    assert _moteur()._calculer_ajustement(correspondances) == 0


# -------------------------------------------------------------
#  Pile au seuil de 70 % -> ajustement non nul mais d'amplitude 0
# -------------------------------------------------------------

def test_ajustement_au_seuil_amplitude_nulle():
    """À exactement 70 %, la proportion vaut 0 : amplitude nulle."""
    correspondances = [
        _correspondance("A", "fake", 70.0),
        _correspondance("B", "fake", 70.0),
    ]
    # Le seuil est atteint (≥ 70) mais l'amplitude graduée vaut 0.
    assert _moteur()._calculer_ajustement(correspondances) == 0


# -------------------------------------------------------------
#  Égalité parfaite fake/real -> ajustement neutre
# -------------------------------------------------------------

def test_ajustement_egalite_est_neutre():
    """Autant de fake que de real : aucune direction nette -> 0."""
    correspondances = [
        _correspondance("A", "fake", 90.0),
        _correspondance("B", "real", 88.0),
    ]
    assert _moteur()._calculer_ajustement(correspondances) == 0


# -------------------------------------------------------------
#  Liste vide -> ajustement neutre
# -------------------------------------------------------------

def test_ajustement_liste_vide_est_neutre():
    """Aucune correspondance : ajustement neutre (0)."""
    assert _moteur()._calculer_ajustement([]) == 0


# -------------------------------------------------------------
#  Amplitude maximale à 100 % -> borne ±20
# -------------------------------------------------------------

def test_ajustement_amplitude_maximale_bornee():
    """À 100 %, l'amplitude atteint la borne (±20)."""
    moteur = _moteur()

    fake = [
        _correspondance("A", "fake", 100.0),
        _correspondance("B", "fake", 100.0),
    ]
    assert moteur._calculer_ajustement(fake) == -20

    real = [
        _correspondance("A", "real", 100.0),
        _correspondance("B", "real", 100.0),
    ]
    assert moteur._calculer_ajustement(real) == 20


# -------------------------------------------------------------
#  Indisponibilité : résultat neutre via comparer (exigence 9.2)
# -------------------------------------------------------------

def test_comparer_indisponible_ajustement_nul():
    """Sans persistance, comparer renvoie disponible=False,
    correspondances=[] et ajustement_score=0 (exigence 9.2)."""
    resultat = _moteur().comparer(Article("Titre", "un contenu", None))
    assert resultat == {
        "disponible": False,
        "correspondances": [],
        "ajustement_score": 0,
    }
