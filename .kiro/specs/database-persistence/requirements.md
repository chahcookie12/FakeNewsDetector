# Requirements Document

## Introduction

Cette fonctionnalité ajoute une couche de **persistance locale** au projet FakeNewsDetector
(Phase 2 du cahier des charges). Aujourd'hui, chaque analyse de texte produit un score, un
verdict et un détail, mais ces résultats sont perdus dès que le programme se ferme.

L'objectif est de créer une classe `BaseDeDonnees` qui s'appuie sur **SQLite** (module
`sqlite3` intégré à Python, sans serveur) pour :

- enregistrer automatiquement chaque article analysé avec son score, son verdict et ses indicateurs ;
- consulter l'historique des analyses passées, triées par date ;
- préparer (sous forme de table et de méthode « stub ») une base de référence d'articles
  fiables qui sera réellement exploitée dans une phase ultérieure.

La fonctionnalité doit aussi s'intégrer au menu console existant de `main.py` :
sauvegarde automatique après chaque analyse, et nouvelle option de menu pour afficher
l'historique.

**Hors périmètre (phases ultérieures, explicitement reportées) :** import de jeux de données
externes, appels à une News API, calcul de similarité avec la base de référence.

Le projet est pédagogique (ENSIAS, 1ère année) : le code et la conception doivent rester
**simples, lisibles et bien commentés**.

## Glossary

- **BaseDeDonnees** : Classe Python responsable de toutes les opérations de persistance via SQLite. Système principal de cette fonctionnalité.
- **Article** : Objet existant représentant un texte à analyser (attributs : `titre`, `contenu`, `source`, `date`) ; fournit une méthode `to_dict()`.
- **Analyseur** : Classe existante qui extrait des indicateurs mesurables d'un texte.
- **Score_Classe** : Classe existante qui produit un dictionnaire `{score, verdict, detail}` à partir des indicateurs.
- **Analyse** : Enregistrement combinant un Article et son résultat de scoring (score, verdict, indicateurs/détail).
- **Score** : Entier de 0 à 100 mesurant la crédibilité estimée d'un Article.
- **Verdict** : Étiquette textuelle parmi `FAKE`, `DOUTEUX`, `FIABLE`.
- **Indicateurs** : Dictionnaire produit par l'Analyseur (nb_mots, mots_suspects, etc.).
- **Detail** : Liste de lignes textuelles expliquant le calcul du score, produite par la classe Score_Classe.
- **Historique** : Ensemble des Analyses enregistrées, présentées triées par date décroissante.
- **Base_De_Reference** : Table SQLite destinée à stocker des articles réputés fiables (`contenus_fiables`), prévue pour un usage futur de comparaison de similarité.
- **Fichier_Base** : Fichier SQLite local situé à `data/fakenews.db`.
- **Schema** : Ensemble des tables et colonnes de la base de données.
- **Menu_Console** : Interface texte de `main.py` permettant à l'utilisateur de choisir une action.

## Requirements

### Requirement 1: Initialisation de la base et création du schéma

**User Story:** En tant que développeur, je veux que la base de données et ses tables soient créées automatiquement au démarrage, afin de ne pas avoir à les configurer manuellement.

#### Acceptance Criteria

1. WHEN une instance de BaseDeDonnees est créée, THE BaseDeDonnees SHALL établir une connexion SQLite vers le Fichier_Base situé à `data/fakenews.db`.
2. IF le Fichier_Base n'existe pas au moment de la connexion, THEN THE BaseDeDonnees SHALL créer un nouveau Fichier_Base à `data/fakenews.db`.
3. WHEN une instance de BaseDeDonnees est créée, THE BaseDeDonnees SHALL créer la table des Analyses si cette table n'existe pas déjà.
4. WHEN une instance de BaseDeDonnees est créée, THE BaseDeDonnees SHALL créer la table Base_De_Reference (`contenus_fiables`) si cette table n'existe pas déjà.
5. THE table des Analyses SHALL contenir les colonnes : identifiant unique, titre, contenu, source, date, score, verdict et détail des indicateurs.
6. WHEN une instance de BaseDeDonnees est créée alors que le Fichier_Base et ses tables existent déjà, THE BaseDeDonnees SHALL conserver l'intégralité des lignes existantes des tables sans les supprimer, écraser ni réinitialiser.
7. IF la création du Schema échoue (par exemple manque d'espace disque, corruption du Fichier_Base ou erreur de transaction), THEN THE BaseDeDonnees SHALL interrompre l'initialisation, annuler toute transaction de création en cours afin qu'aucune table ne reste partiellement créée, et signaler l'échec à l'appelant par une erreur explicite.
8. IF la connexion SQLite vers le Fichier_Base ne peut pas être établie au moment de l'initialisation, THEN THE BaseDeDonnees SHALL interrompre l'initialisation et signaler l'échec à l'appelant par une erreur explicite.

### Requirement 2: Enregistrement d'une analyse

**User Story:** En tant qu'utilisateur, je veux que chaque texte analysé soit enregistré avec son résultat, afin de conserver une trace de mes analyses.

#### Acceptance Criteria

1. WHEN une Analyse est soumise à l'enregistrement, THE BaseDeDonnees SHALL insérer une nouvelle ligne dans la table des Analyses contenant le titre, le contenu, la source et la date de l'Article.
2. WHEN une Analyse est soumise à l'enregistrement, THE BaseDeDonnees SHALL insérer dans cette même ligne le score (entier de 0 à 100), le verdict (`FAKE`, `DOUTEUX` ou `FIABLE`) et le détail explicatif sous forme textuelle conservant l'ensemble des lignes des indicateurs associés à l'Article.
3. WHEN une Analyse est enregistrée, THE BaseDeDonnees SHALL stocker la date au format texte `AAAA-MM-JJ HH:MM:SS`.
4. WHEN une Analyse est enregistrée avec succès, THE BaseDeDonnees SHALL valider la transaction (commit) afin que la donnée soit durablement écrite dans le Fichier_Base.
5. IF l'enregistrement d'une Analyse échoue, THEN THE BaseDeDonnees SHALL ne pas valider la transaction (aucun commit) et SHALL garantir qu'aucune ligne correspondant à cette Analyse ne subsiste dans la table des Analyses.
6. WHEN une Analyse est enregistrée avec succès, THE BaseDeDonnees SHALL retourner l'identifiant unique (entier strictement positif) de la ligne créée.
7. IF la source d'un Article est absente (valeur nulle ou chaîne vide), THEN THE BaseDeDonnees SHALL enregistrer la valeur `Inconnue` dans la colonne source.
8. IF l'enregistrement d'une Analyse échoue, THEN THE BaseDeDonnees SHALL signaler l'échec à l'appelant sans retourner d'identifiant de ligne.

### Requirement 3: Sauvegarde automatique après analyse

**User Story:** En tant qu'utilisateur, je veux que mon analyse soit sauvegardée automatiquement après le scoring, afin de ne pas avoir à déclencher l'enregistrement manuellement.

#### Acceptance Criteria

1. WHEN une analyse de texte se termine avec un score calculé dans le Menu_Console, THE Menu_Console SHALL transmettre à la BaseDeDonnees, sans action manuelle de l'utilisateur, l'Article accompagné de son score, de son verdict et du détail des indicateurs pour enregistrement.
2. WHEN l'enregistrement automatique réussit, THE Menu_Console SHALL afficher un message de confirmation indiquant que l'analyse a été enregistrée.
3. IF l'affichage du message de confirmation échoue, THEN THE Menu_Console SHALL poursuivre l'exécution du programme sans afficher la confirmation.
4. IF l'enregistrement automatique échoue, THEN THE Menu_Console SHALL afficher un message d'erreur indiquant que la sauvegarde de l'analyse a échoué.
5. IF l'enregistrement automatique échoue, THEN THE Menu_Console SHALL poursuivre l'exécution du programme et conserver le résultat de l'analyse affiché à l'utilisateur.

### Requirement 4: Consultation de l'historique

**User Story:** En tant qu'utilisateur, je veux consulter la liste de mes analyses passées, afin de revoir les résultats précédents.

#### Acceptance Criteria

1. WHEN l'historique est demandé, THE BaseDeDonnees SHALL retourner les Analyses enregistrées triées par date décroissante (la plus récente en premier), et à dates identiques triées par identifiant unique décroissant.
2. WHEN l'historique est demandé, THE BaseDeDonnees SHALL inclure pour chaque Analyse le titre, le score, le verdict et la date.
3. WHEN l'utilisateur choisit l'option d'historique dans le Menu_Console, THE Menu_Console SHALL afficher chaque Analyse avec son titre, son score, son verdict et sa date.
4. IF l'historique ne contient aucune Analyse, THEN THE Menu_Console SHALL afficher un message indiquant que l'historique est vide.
5. WHERE un nombre maximum de résultats supérieur ou égal à 1 est fourni, THE BaseDeDonnees SHALL limiter le nombre d'Analyses retournées à ce nombre, et SHALL retourner toutes les Analyses enregistrées lorsque ce nombre dépasse le nombre d'Analyses enregistrées.
6. WHEN l'historique est demandé sans nombre maximum de résultats, THE BaseDeDonnees SHALL retourner toutes les Analyses enregistrées.
7. IF un nombre maximum de résultats inférieur à 1 est fourni, THEN THE BaseDeDonnees SHALL signaler une erreur à l'appelant et SHALL ne retourner aucune Analyse.
8. IF la récupération de l'historique échoue, THEN THE Menu_Console SHALL afficher un message d'erreur lisible et SHALL poursuivre l'exécution du programme.

### Requirement 5: Base de référence d'articles fiables (préparation)

**User Story:** En tant que développeur, je veux préparer une base de référence d'articles fiables, afin de pouvoir l'exploiter pour la comparaison de similarité dans une phase future.

#### Acceptance Criteria

1. WHEN un contenu fiable est soumis à l'ajout, THE BaseDeDonnees SHALL insérer dans la table Base_De_Reference le titre, le contenu et la source du contenu fiable.
2. WHEN les contenus fiables enregistrés sont demandés, THE BaseDeDonnees SHALL retourner pour chaque contenu fiable son identifiant unique, son titre, son contenu et sa source.
3. THE table Base_De_Reference SHALL contenir les colonnes : identifiant unique, titre, contenu et source.
4. THE documentation de la méthode d'ajout de contenu fiable SHALL indiquer que l'usage de similarité est prévu pour une phase ultérieure.
5. IF la table Base_De_Reference ne contient aucun contenu fiable lorsqu'une récupération est demandée, THEN THE BaseDeDonnees SHALL retourner une collection vide.
6. IF la source d'un contenu fiable est absente lors de l'ajout, THEN THE BaseDeDonnees SHALL enregistrer la valeur `Inconnue` dans la colonne source.
7. WHEN un contenu fiable est ajouté avec succès, THE BaseDeDonnees SHALL valider la transaction (commit) afin que le contenu soit durablement écrit dans le Fichier_Base.

### Requirement 6: Gestion des erreurs et robustesse

**User Story:** En tant qu'utilisateur, je veux que le programme reste stable même en cas de problème avec la base de données, afin de ne pas perdre l'usage de l'application.

#### Acceptance Criteria

1. IF une erreur SQLite survient pendant une opération de base de données, THEN THE BaseDeDonnees SHALL signaler l'erreur à l'appelant avec un message identifiant l'opération concernée et la nature de l'erreur SQLite.
2. IF le Fichier_Base est verrouillé lors d'une opération d'écriture, THEN THE BaseDeDonnees SHALL signaler l'erreur de verrouillage comme une erreur récupérable, sans provoquer l'arrêt du processus du programme.
3. IF une opération d'écriture échoue après ouverture d'une transaction, THEN THE BaseDeDonnees SHALL annuler toute transaction ouverte (rollback), que des données aient été écrites ou non, afin de préserver la cohérence des données.
4. THE BaseDeDonnees SHALL fournir une méthode permettant de fermer la connexion SQLite.
5. IF le dossier `data` n'existe pas au moment de la connexion, THEN THE BaseDeDonnees SHALL créer le dossier `data` avant d'ouvrir le Fichier_Base.
6. WHEN la méthode de fermeture de la connexion est appelée, THE BaseDeDonnees SHALL fermer la connexion SQLite active.
7. IF la création du dossier `data` échoue, THEN THE BaseDeDonnees SHALL signaler l'échec à l'appelant par une erreur explicite.
