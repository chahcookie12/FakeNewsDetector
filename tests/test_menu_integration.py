# =============================================================
#  Tests d'intégration du menu console (task 6.4)
# =============================================================
#
#  Vérifie l'intégration entre main.py et BaseDeDonnees :
#  sauvegarde automatique, messages de confirmation / erreur,
#  affichage de l'historique, et résilience aux échecs.
#
#  Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 4.3, 4.4, 4.8

from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime

import pytest

from classes.base_donnees import ErreurBaseDeDonnees
from main import analyser_texte, afficher_historique


# =============================================================
#  Fixtures et helpers
# =============================================================

def _mock_analyseur():
    """Crée un analyseur mocké retournant des indicateurs valides."""
    analyseur = MagicMock()
    analyseur.analyser.return_value = {
        "nb_mots": 100,
        "nb_mots_uniques": 60,
        "sources_presentes": True,
        "mots_suspects": None,
        "frequences": {"le": 5, "de": 4},
    }
    return analyseur


def _mock_scoreur():
    """Crée un scoreur mocké retournant un résultat valide."""
    scoreur = MagicMock()
    scoreur.calculer.return_value = {
        "score": 75,
        "verdict": "FIABLE",
        "detail": ["Score de base : 50", "+25 sources citées"],
    }
    scoreur.afficher.return_value = None
    return scoreur


def _mock_base(enregistrer_id=42):
    """Crée une BaseDeDonnees mockée (enregistrer retourne un id)."""
    base = MagicMock()
    base.enregistrer_analyse.return_value = enregistrer_id
    return base


def _inputs_article():
    """Simule la saisie d'un article complet (titre, contenu, source)."""
    # titre, ligne de contenu, ligne vide (1ère), ligne vide (2ème = fin),
    # source
    return iter([
        "Mon titre",       # titre
        "Du texte ici",    # contenu ligne 1
        "",                # première ligne vide (ajoutée à lignes)
        "",                # deuxième ligne vide = fin de saisie
        "lemonde.fr",      # source
    ])


# =============================================================
#  3.1 — Sauvegarde automatique après analyse
# =============================================================
def test_sauvegarde_auto_apres_analyse(monkeypatch, capsys):
    """enregistrer_analyse est appelé automatiquement après scoring."""

    inputs = _inputs_article()
    monkeypatch.setattr("builtins.input", lambda *a, **kw: next(inputs))

    analyseur = _mock_analyseur()
    scoreur = _mock_scoreur()
    base = _mock_base(enregistrer_id=7)

    analyser_texte(analyseur, scoreur, base)

    # enregistrer_analyse a été appelé exactement une fois.
    base.enregistrer_analyse.assert_called_once()


# =============================================================
#  3.2 — Message de confirmation avec l'identifiant
# =============================================================
def test_confirmation_avec_id(monkeypatch, capsys):
    """Un message de confirmation contenant l'id est affiché."""

    inputs = _inputs_article()
    monkeypatch.setattr("builtins.input", lambda *a, **kw: next(inputs))

    analyseur = _mock_analyseur()
    scoreur = _mock_scoreur()
    base = _mock_base(enregistrer_id=42)

    analyser_texte(analyseur, scoreur, base)

    sortie = capsys.readouterr().out
    assert "42" in sortie
    assert "enregistr" in sortie.lower()


# =============================================================
#  3.3 — Programme continue si affichage de confirmation échoue
# =============================================================
def test_poursuite_si_affichage_confirmation_echoue(monkeypatch, capsys):
    """Si print échoue lors de la confirmation, pas de crash."""

    inputs = _inputs_article()
    monkeypatch.setattr("builtins.input", lambda *a, **kw: next(inputs))

    analyseur = _mock_analyseur()
    scoreur = _mock_scoreur()
    base = _mock_base(enregistrer_id=10)

    # On compte les appels à print. On fait échouer uniquement
    # l'appel qui contient le numéro d'identifiant.
    original_print = print
    call_count = {"n": 0}

    def print_qui_echoue(*args, **kwargs):
        text = " ".join(str(a) for a in args)
        if "#10" in text or "enregistr" in text.lower():
            raise OSError("simulated display failure")
        original_print(*args, **kwargs)

    monkeypatch.setattr("builtins.print", print_qui_echoue)

    # Ne doit pas lever d'exception.
    analyser_texte(analyseur, scoreur, base)


# =============================================================
#  3.4 — Message d'erreur si sauvegarde échoue
# =============================================================
def test_message_erreur_sauvegarde(monkeypatch, capsys):
    """Si enregistrer_analyse lève ErreurBaseDeDonnees, un message
    d'erreur de sauvegarde apparaît."""

    inputs = _inputs_article()
    monkeypatch.setattr("builtins.input", lambda *a, **kw: next(inputs))

    analyseur = _mock_analyseur()
    scoreur = _mock_scoreur()
    base = MagicMock()
    base.enregistrer_analyse.side_effect = ErreurBaseDeDonnees("DB locked")

    analyser_texte(analyseur, scoreur, base)

    sortie = capsys.readouterr().out.lower()
    assert "sauvegarde" in sortie and "échouée" in sortie or "echouée" in sortie or "échouée" in sortie


# =============================================================
#  3.5 — Programme continue et résultat affiché après échec
# =============================================================
def test_resultat_affiche_malgre_echec_sauvegarde(monkeypatch, capsys):
    """Le résultat (score/verdict) est affiché même si la sauvegarde
    échoue. Le programme ne crashe pas."""

    inputs = _inputs_article()
    monkeypatch.setattr("builtins.input", lambda *a, **kw: next(inputs))

    analyseur = _mock_analyseur()
    scoreur = _mock_scoreur()
    base = MagicMock()
    base.enregistrer_analyse.side_effect = ErreurBaseDeDonnees("write error")

    # Ne doit pas lever d'exception.
    analyser_texte(analyseur, scoreur, base)

    # scoreur.afficher a été appelé (le résultat a été affiché).
    scoreur.afficher.assert_called_once()


# =============================================================
#  4.3 — Affichage de l'historique (titre, score, verdict, date)
# =============================================================
def test_affichage_historique(monkeypatch, capsys):
    """L'historique affiché contient titre, score, verdict et date."""

    base = MagicMock()
    base.recuperer_historique.return_value = [
        {
            "id": 1,
            "titre": "Article Test",
            "score": 65,
            "verdict": "DOUTEUX",
            "date": "2024-06-15 10:30:00",
        }
    ]

    afficher_historique(base)

    sortie = capsys.readouterr().out
    assert "Article Test" in sortie
    assert "65" in sortie
    assert "DOUTEUX" in sortie
    assert "2024-06-15" in sortie


# =============================================================
#  4.4 — Message d'historique vide
# =============================================================
def test_historique_vide_message(monkeypatch, capsys):
    """Si l'historique est vide, un message dédié s'affiche."""

    base = MagicMock()
    base.recuperer_historique.return_value = []

    afficher_historique(base)

    sortie = capsys.readouterr().out.lower()
    assert "vide" in sortie


# =============================================================
#  4.8 — Message lisible si récupération de l'historique échoue
# =============================================================
def test_erreur_historique_message_lisible(monkeypatch, capsys):
    """Si recuperer_historique lève ErreurBaseDeDonnees, un message
    d'erreur lisible est affiché et le programme continue."""

    base = MagicMock()
    base.recuperer_historique.side_effect = ErreurBaseDeDonnees(
        "Récupération de l'historique : échec de la lecture"
    )

    # Ne doit pas lever d'exception.
    afficher_historique(base)

    sortie = capsys.readouterr().out.lower()
    assert "historique" in sortie or "impossible" in sortie or "erreur" in sortie
