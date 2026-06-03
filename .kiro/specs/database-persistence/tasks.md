# Implementation Plan: Database Persistence

## Overview

Cette fonctionnalité ajoute une couche de persistance locale (SQLite) au projet
FakeNewsDetector via une nouvelle classe `BaseDeDonnees` (`classes/base_donnees.py`) et
l'intègre au menu console (`main.py`).

L'implémentation est **incrémentale** : on construit d'abord la fondation (exception métier,
connexion, schéma), puis le chemin d'écriture (`enregistrer_analyse`), puis le chemin de
lecture (`recuperer_historique`), puis la base de référence, et enfin l'intégration au menu
console qui relie le tout. Chaque étape s'appuie sur la précédente et se termine par du code
réellement câblé, sans code orphelin.

Les tests de propriétés (bibliothèque **Hypothesis**, ≥ 100 itérations chacun) couvrent les 9
propriétés de correction du design. Les tests par l'exemple couvrent la configuration, le
schéma, les conditions d'erreur et l'intégration au menu. Tous les tests utilisent une base
temporaire/isolée pour rester rapides et sans effet de bord.

- **Langage** : Python (cohérent avec le projet existant).
- **Tests par l'exemple** : `pytest`.
- **Tests de propriétés** : `Hypothesis` (`@settings(max_examples=100)`).
- **Traçabilité PBT** : chaque test de propriété porte un commentaire
  `Feature: database-persistence, Property {n}: {texte}`.

## Tasks

- [ ] 1. Fondation de la persistance (exception, connexion, schéma)
  - [x] 1.1 Implémenter `ErreurBaseDeDonnees` et l'initialisation de `BaseDeDonnees`
    - Créer `classes/base_donnees.py` avec l'exception métier `ErreurBaseDeDonnees`
      (message identifiant l'opération concernée et la nature de l'erreur SQLite)
    - Implémenter `__init__(self, chemin="data/fakenews.db")` : créer le dossier `data` si
      absent (`os.makedirs(..., exist_ok=True)`), ouvrir la connexion SQLite, appeler
      `_creer_schema()`
    - Implémenter `_creer_schema()` : `CREATE TABLE IF NOT EXISTS analyses (...)` et
      `contenus_fiables (...)` selon les schémas du design ; transactionnel (rollback si échec)
    - Implémenter `fermer()` : ferme la connexion SQLite active
    - Lever `ErreurBaseDeDonnees` si la connexion échoue, si la création du dossier échoue, ou
      si la création du schéma échoue (avec rollback, aucune table partielle)
    - Préserver les lignes existantes lorsque le fichier et les tables existent déjà
    - Documenter la table `contenus_fiables` comme préparation d'un usage futur de similarité
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 5.3, 6.4, 6.5, 6.6, 6.7_

  - [ ]* 1.2 Écrire les tests de configuration et de schéma (smoke)
    - Fichier : `tests/test_config_schema.py`
    - Vérifier : connexion établie (1.1), fichier `fakenews.db` créé (1.2), tables `analyses`
      (1.3) et `contenus_fiables` (1.4) présentes, colonnes attendues via `PRAGMA table_info`
      (1.5, 5.3), présence de `fermer()` (6.4), fermeture effective de la connexion (6.6),
      docstring mentionnant l'usage futur de similarité (5.4)
    - Vérifier la préservation des lignes à la réouverture du même fichier (1.6)
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 5.3, 5.4, 6.4, 6.6_

  - [x]* 1.3 Écrire les tests unitaires des erreurs d'initialisation
    - Fichier : `tests/test_init_erreurs.py`
    - Simuler : échec de création du schéma avec rollback (1.7), connexion impossible (1.8),
      échec de création du dossier `data` (6.7) — via chemin invalide / mock du curseur
    - Vérifier qu'une `ErreurBaseDeDonnees` explicite est levée dans chaque cas
    - _Requirements: 1.7, 1.8, 6.5, 6.7_

- [ ] 2. Enregistrement d'une analyse
  - [x] 2.1 Implémenter `enregistrer_analyse` et la (dé)sérialisation du détail
    - Ajouter `enregistrer_analyse(self, article, resultat)` à `classes/base_donnees.py`
    - Insérer titre, contenu, source, date, score, verdict, détail dans `analyses`
    - Normaliser la source : `None` / chaîne vide / espaces → `Inconnue`
    - Formater la date depuis `article.date` en `"%Y-%m-%d %H:%M:%S"`
    - Ajouter les helpers internes `_serialiser_detail` (`"\n".join(...)`) et
      `_deserialiser_detail` (`split("\n")`) pour préserver les lignes et leur ordre
    - `commit()` en cas de succès et retourner l'identifiant créé (entier strictement positif) ;
      `rollback()` + `ErreurBaseDeDonnees` en cas d'échec, sans retourner d'identifiant et sans
      laisser de ligne résiduelle
    - Encapsuler les `sqlite3.Error` (dont fichier verrouillé) en `ErreurBaseDeDonnees`
      récupérable
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 6.1, 6.2, 6.3_

  - [ ]* 2.2 Test de propriété — sérialisation du détail
    - Fichier : `tests/test_prop2_detail.py`
    - **Property 2: Round-trip de sérialisation du détail**
    - Vérifier `_deserialiser_detail(_serialiser_detail(lignes)) == lignes` (intégralité et ordre)
    - **Validates: Requirements 2.2**

  - [ ]* 2.3 Test de propriété — identifiant unique et strictement positif
    - Fichier : `tests/test_prop4_id.py`
    - **Property 4: Identifiant unique et strictement positif**
    - Pour une suite d'enregistrements réussis, chaque id retourné est > 0 et tous distincts
    - **Validates: Requirements 2.6**

  - [x]* 2.4 Écrire les tests unitaires des erreurs d'enregistrement
    - Fichier : `tests/test_enregistrement_erreurs.py`
    - Vérifier : échec d'enregistrement → rollback, aucune ligne résiduelle, aucun id retourné
      (2.5, 2.8, 6.3) ; message d'erreur identifiant l'opération (6.1) ; fichier verrouillé
      signalé comme récupérable sans arrêt du processus (6.2) — via base corrompue / mock /
      seconde connexion verrouillante
    - _Requirements: 2.5, 2.8, 6.1, 6.2, 6.3_

- [ ] 3. Consultation de l'historique
  - [x] 3.1 Implémenter `recuperer_historique`
    - Ajouter `recuperer_historique(self, limite=None)` à `classes/base_donnees.py`
    - Trier par `date DESC` puis `id DESC` ; retourner une liste de dict
      `{id, titre, score, verdict, date}`
    - `limite=None` → toutes les analyses ; `limite >= 1` → au plus `limite` (toutes si la
      limite dépasse le nombre d'analyses)
    - `limite < 1` → lever `ErreurBaseDeDonnees`, ne retourner aucune analyse
    - Encapsuler les `sqlite3.Error` en `ErreurBaseDeDonnees`
    - _Requirements: 4.1, 4.2, 4.5, 4.6, 4.7_

  - [ ]* 3.2 Test de propriété — round-trip de persistance d'une analyse
    - Fichier : `tests/test_prop1_roundtrip.py`
    - **Property 1: Round-trip de persistance d'une analyse**
    - Enregistrer un ensemble d'analyses, relire (y compris après `fermer()` puis réouverture du
      même fichier) ; vérifier titre, score, verdict, date conservés et aucune ligne perdue
    - **Validates: Requirements 1.6, 2.1, 2.2, 2.4, 4.2**

  - [ ]* 3.3 Test de propriété — format de date canonique
    - Fichier : `tests/test_prop3_date.py`
    - **Property 3: Format de date canonique**
    - La date relue respecte exactement `AAAA-MM-JJ HH:MM:SS` et correspond à la date d'origine
      formatée
    - **Validates: Requirements 2.3**

  - [ ]* 3.4 Test de propriété — ordre de l'historique
    - Fichier : `tests/test_prop6_ordre.py`
    - **Property 6: Ordre de l'historique**
    - Pour des analyses aux dates éventuellement identiques, l'historique est trié par date
      décroissante puis par id décroissant
    - **Validates: Requirements 4.1**

  - [ ]* 3.5 Test de propriété — limite de l'historique
    - Fichier : `tests/test_prop7_limite.py`
    - **Property 7: Limite de l'historique**
    - Pour N analyses et une limite L : `min(L, N)` analyses si `L >= 1`, toutes si aucune
      limite ; les analyses retournées sont les plus récentes selon l'ordre défini
    - **Validates: Requirements 4.5, 4.6**

  - [ ]* 3.6 Test de propriété — erreur sur limite invalide
    - Fichier : `tests/test_prop8_limite_invalide.py`
    - **Property 8: Erreur sur limite invalide**
    - Pour toute limite `< 1`, la récupération signale une erreur et ne retourne aucune analyse
    - **Validates: Requirements 4.7**

- [ ] 4. Checkpoint
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Base de référence d'articles fiables (préparation)
  - [x] 5.1 Implémenter `ajouter_contenu_fiable` et `recuperer_contenus_fiables`
    - Ajouter `ajouter_contenu_fiable(self, titre, contenu, source=None)` : insère dans
      `contenus_fiables`, normalise la source absente en `Inconnue`, `commit()` en cas de succès
      et retourne l'identifiant créé, `rollback()` + `ErreurBaseDeDonnees` sinon
    - La docstring indique que l'exploitation par similarité est prévue pour une phase ultérieure
    - Ajouter `recuperer_contenus_fiables(self)` : retourne une liste de dict
      `{id, titre, contenu, source}`, liste vide si aucun contenu
    - _Requirements: 5.1, 5.2, 5.4, 5.5, 5.6, 5.7_

  - [ ]* 5.2 Test de propriété — round-trip de la base de référence
    - Fichier : `tests/test_prop9_reference.py`
    - **Property 9: Round-trip de la base de référence**
    - Les contenus ajoutés sont récupérés avec id, titre, contenu et source ; récupération vide
      si aucun ajout
    - **Validates: Requirements 5.1, 5.2, 5.5, 5.7**

  - [ ]* 5.3 Test de propriété — normalisation de la source absente
    - Fichier : `tests/test_prop5_source.py`
    - **Property 5: Normalisation de la source absente**
    - Pour tout contenu inséré (analyse ou contenu fiable) : source nulle/espaces → `Inconnue`,
      sinon source conservée (lecture de la source via `recuperer_contenus_fiables` et requête
      directe sur la table `analyses`)
    - **Validates: Requirements 2.7, 5.6**

- [ ] 6. Intégration au menu console (`main.py`)
  - [x] 6.1 Initialiser `BaseDeDonnees` au démarrage avec dégradation gracieuse
    - Dans `main()`, créer une instance `BaseDeDonnees()` au démarrage
    - En cas d'`ErreurBaseDeDonnees`, afficher un avertissement et continuer sans persistance
      (la base reste à `None`, l'analyse demeure utilisable)
    - _Requirements: 1.8, 6.5, 6.7_

  - [x] 6.2 Sauvegarde automatique après analyse
    - À la fin de `analyser_texte`, après l'affichage du résultat, appeler
      `enregistrer_analyse(article, resultat)` sans action manuelle de l'utilisateur
    - Succès → message de confirmation avec l'identifiant ; si l'affichage de la confirmation
      échoue, poursuivre sans l'afficher
    - Échec d'enregistrement → message « sauvegarde échouée », poursuite du programme, résultat
      toujours affiché
    - Passer l'instance `BaseDeDonnees` à `analyser_texte`
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 6.3 Option d'historique et fermeture à la sortie
    - Ajouter l'option « 2. Afficher l'historique » au menu : appeler `recuperer_historique()`
      et afficher chaque analyse (titre, score, verdict, date)
    - Historique vide → message dédié ; erreur de récupération → message lisible, poursuite
    - Appeler `fermer()` avant de quitter (choix « 0 »)
    - _Requirements: 4.3, 4.4, 4.8, 6.4, 6.6_

  - [x]* 6.4 Écrire les tests d'intégration du menu console
    - Fichier : `tests/test_menu_integration.py`
    - Vérifier : transmission automatique de l'analyse (3.1), message de confirmation (3.2),
      poursuite si l'affichage échoue (3.3), message d'erreur de sauvegarde (3.4), poursuite +
      conservation du résultat affiché (3.5), rendu de l'historique (4.3), message d'historique
      vide (4.4), message lisible si récupération échoue (4.8) — via capture de sortie et mocks
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 4.3, 4.4, 4.8_

- [ ] 7. Checkpoint final
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Les tâches marquées `*` sont des tâches de test, optionnelles, pouvant être ignorées pour un
  MVP plus rapide (mais recommandées pour la traçabilité et la robustesse).
- Chaque tâche référence des critères d'acceptation spécifiques pour la traçabilité.
- Les 9 propriétés de correction du design sont chacune implémentées par un seul test de
  propriété (Hypothesis, ≥ 100 itérations), placé au plus près de l'implémentation concernée.
- Les tests par l'exemple ciblent la configuration/schéma, les conditions d'erreur (rollback,
  verrouillage) et l'intégration au menu console — points difficiles à générer aléatoirement.
- Les checkpoints assurent une validation incrémentale.
- Chaque test de propriété est dans son propre fichier pour permettre une exécution parallèle et
  éviter les conflits d'écriture.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2", "1.3", "2.1", "6.1"] },
    { "id": 2, "tasks": ["2.2", "2.3", "2.4", "3.1", "6.2"] },
    { "id": 3, "tasks": ["3.2", "3.3", "3.4", "3.5", "3.6", "5.1", "6.3"] },
    { "id": 4, "tasks": ["5.2", "5.3", "6.4"] }
  ]
}
```
