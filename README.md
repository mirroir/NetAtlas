# NetAtlas

[![NetAtlas
Tests](https://github.com/mirroir/NetAtlas/actions/workflows/tests.yml/badge.svg)](https://github.com/mirroir/NetAtlas/actions/workflows/tests.yml)

> Laboratoire Python / PostgreSQL orienté recherche, tests automatisés,
> qualité de service et pratiques DevOps.

NetAtlas est un projet personnel de laboratoire permettant d'explorer
des lieux à partir d'un moteur de recherche global multi-critères. Le
projet associe une base PostgreSQL structurée, une application Python en
ligne de commande, une interface Web Flask, des tests automatisés et une
intégration continue avec GitHub Actions.

L'objectif n'est pas seulement de développer une application
fonctionnelle : NetAtlas sert également de support pratique pour
travailler l'administration des données, l'automatisation, la qualité
logicielle, la sécurité et les problématiques d'exploitation proches
d'un environnement OPS / DevOps.

## 🎯 Objectifs du projet

-   Concevoir et administrer une base PostgreSQL structurée.
-   Développer une application Python connectée à PostgreSQL.
-   Proposer une utilisation en ligne de commande et via une interface
    Web.
-   Construire un moteur de recherche global multi-critères et tolérant.
-   Gérer des lieux, catégories, tags, services et commentaires.
-   Permettre aux utilisateurs authentifiés d'interagir avec les lieux.
-   Mettre en place une batterie de tests automatisés.
-   Contrôler la qualité du code et le fonctionnement global de
    l'application.
-   Sécuriser les données de configuration et les secrets.
-   Automatiser les contrôles avec une chaîne d'intégration continue.
-   Faire évoluer progressivement le projet vers une démarche DevOps
    complète.

## 🏗️ Architecture technique

NetAtlas est organisé en plusieurs couches afin de séparer les
responsabilités :

-   **PostgreSQL** : stockage, relations et intégrité des données.
-   **Python** : logique applicative et accès à la base de données.
-   **CLI** : navigation et interaction depuis le terminal.
-   **Flask** : interface Web de l'application.
-   **pytest** : validation automatisée du comportement.
-   **Ruff** : contrôle de la qualité du code Python.
-   **Shell / Bash** : automatisation des contrôles du projet.
-   **Git / GitHub** : versionnement et intégration continue.

### Organisation simplifiée

``` text
NetAtlas/
├── database/          Scripts SQL, schémas et données de test
├── python/
│   ├── database.py    Accès PostgreSQL et requêtes
│   ├── main.py        Boucle principale de l'application CLI
│   └── menu.py        Interface utilisateur CLI
├── web/
│   ├── app.py         Application Web Flask
│   ├── templates/     Pages HTML
│   └── static/        Ressources CSS
├── scripts/           Scripts de contrôle et d'automatisation
├── tests/             Tests automatisés
├── .github/           Configuration GitHub Actions
├── .gitignore         Protection des fichiers locaux et sensibles
└── README.md          Documentation publique du projet
```

## 🌍 Modèle géographique

NetAtlas utilise une organisation géographique hiérarchique :

``` text
Pays
└── Territoire
    └── Région
        └── Ville
            └── Lieu
```

Cette branche est exploitée par le moteur de recherche global. Un lieu
peut ainsi être retrouvé à partir de son pays, de son territoire, de sa
région ou de sa ville.

## 🔎 Moteur de recherche global

Le moteur de recherche constitue le point central de navigation dans
NetAtlas. Il interroge notamment le nom du lieu, la ville, la région, le
territoire, le pays, la catégorie, la description, les tags et les
services.

La recherche combine :

-   `ILIKE` pour une recherche insensible à la casse ;
-   PostgreSQL `pg_trgm` et `similarity()` pour améliorer la tolérance ;
-   un score de pertinence pour ordonner les résultats ;
-   une limitation du nombre de résultats retournés.

## 🖥️ Interfaces utilisateur

### Interface CLI

L'application en ligne de commande permet d'effectuer une recherche
globale, sélectionner un lieu, afficher ses détails et accéder aux
fonctions autorisées selon le type d'utilisateur. Les utilisateurs
authentifiés peuvent notamment gérer leurs commentaires et ajouter des
tags aux lieux.

### Interface Web Flask

NetAtlas dispose également d'une interface Web Flask permettant
notamment :

-   un accès temporaire en consultation ;
-   la création et la connexion d'un profil utilisateur ;
-   la recherche globale ;
-   l'affichage détaillé d'un lieu ;
-   la consultation des tags, services et commentaires ;
-   l'ajout de commentaires pour les utilisateurs authentifiés ;
-   l'enregistrement d'une réaction positive ou négative sur un lieu.

Les interfaces Web et CLI utilisent la même couche d'accès aux données.

## 🧪 Tests automatisés & qualité de service

La qualité de fonctionnement constitue un axe important du projet.
NetAtlas dispose actuellement de **206 tests automatisés** avec
`pytest`, couvrant notamment les fonctions Python, PostgreSQL, le moteur
de recherche global, les relations et contraintes de la base, les menus
CLI, les tags, les services, les commentaires, les réactions utilisateur
et différents scénarios d'erreur.

Une base dédiée, `netatlas_test`, permet d'isoler les tests de la base
principale. Le schéma SQL et le jeu de données de test permettent de
reconstruire un environnement reproductible.

Contrôle qualité :

``` bash
ruff check .
```

Tests :

``` bash
pytest -q
```

Contrôle global :

``` bash
./scripts/check_netatlas.sh
```

## 🔄 Intégration continue

NetAtlas utilise **GitHub Actions** pour automatiser les contrôles du
projet. Le badge placé en haut de ce README permet de visualiser
rapidement l'état de la dernière exécution de la CI.

## 🔐 Sécurité

Les données locales et sensibles ne sont pas destinées à être
versionnées dans le dépôt public. Le `.gitignore` exclut notamment les
fichiers d'environnement contenant des secrets, l'environnement virtuel
Python, les caches et les configurations locales.

Aucun mot de passe ou jeton d'authentification ne doit être stocké
directement dans le code source. Les requêtes SQL applicatives utilisent
des paramètres afin d'éviter la construction directe de requêtes à
partir des saisies utilisateur.

## ⚙️ Technologies

-   Python
-   PostgreSQL
-   SQL
-   Flask
-   pytest
-   Ruff
-   Bash / Shell
-   Git
-   GitHub
-   GitHub Actions
-   Linux

## 📖 Glossaire

  -----------------------------------------------------------------------
  Terme                               Signification dans NetAtlas
  ----------------------------------- -----------------------------------
  **API**                             Interface permettant à différents
                                      composants logiciels de communiquer
                                      entre eux.

  **CI**                              Intégration continue : exécution
                                      automatisée des contrôles et tests
                                      lors des évolutions du projet.

  **CI/CD**                           Pratiques automatisant
                                      l'intégration et, à terme, la
                                      livraison ou le déploiement.

  **CLI**                             Interface en ligne de commande
                                      utilisée depuis le terminal.

  **DevOps**                          Approche associant développement,
                                      automatisation, tests, exploitation
                                      et déploiement.

  **FK**                              *Foreign Key* : clé étrangère
                                      garantissant une relation entre
                                      deux tables.

  **Flask**                           Framework Python utilisé pour
                                      construire l'interface Web.

  **Git**                             Système de gestion de versions
                                      utilisé pour suivre les évolutions
                                      du projet.

  **GitHub Actions**                  Service utilisé pour exécuter
                                      automatiquement la chaîne
                                      d'intégration continue.

  **ILIKE**                           Opérateur PostgreSQL de recherche
                                      textuelle insensible à la casse.

  **ON DELETE CASCADE**               Règle supprimant automatiquement
                                      les enregistrements dépendants d'un
                                      parent supprimé.

  **PK**                              *Primary Key* : clé primaire
                                      identifiant de manière unique un
                                      enregistrement.

  **pg_trgm**                         Extension PostgreSQL permettant
                                      notamment de mesurer la similarité
                                      entre chaînes de caractères.

  **PostgreSQL**                      Système de gestion de base de
                                      données relationnelle utilisé par
                                      NetAtlas.

  **pytest**                          Framework Python utilisé pour les
                                      tests automatisés.

  **Ruff**                            Outil de contrôle et d'analyse de
                                      la qualité du code Python.

  **SQL**                             Langage utilisé pour créer,
                                      interroger et administrer les
                                      données relationnelles.

  **Territoire**                      Niveau géographique intermédiaire
                                      permettant notamment de rattacher
                                      La Réunion à la France avant ses
                                      régions.

  **Test automatisé**                 Vérification exécutable confirmant
                                      qu'un comportement attendu reste
                                      valide.
  -----------------------------------------------------------------------

## 📌 État du projet

La version actuelle comprend notamment :

-   une base PostgreSQL fonctionnelle et structurée ;
-   une application Python en ligne de commande ;
-   une interface Web Flask ;
-   une gestion de profils et de sessions utilisateur ;
-   un accès temporaire en consultation ;
-   un moteur de recherche global multi-critères ;
-   une recherche tolérante avec `pg_trgm` ;
-   une hiérarchie pays → territoire → région → ville → lieu ;
-   la gestion des tags et services ;
-   un système de commentaires ;
-   des réactions positives ou négatives sur les lieux ;
-   **206 tests automatisés** ;
-   un contrôle qualité avec Ruff ;
-   un script de contrôle global ;
-   une intégration continue avec GitHub Actions ;
-   un dépôt Git public sécurisé.

## 🗺️ Roadmap

1.  Finaliser la consolidation fonctionnelle et documentaire de
    NetAtlas.
2.  Maintenir et enrichir la couverture des tests automatisés.
3.  Poursuivre la simplification et le nettoyage du modèle de données.
4.  Renforcer la configuration et la sécurité avant un environnement
    hors développement.
5.  Faire évoluer GitHub Actions vers une chaîne CI/CD plus complète.
6.  Expérimenter des pratiques DevOps complémentaires avec GitLab et
    Jenkins.
7.  Ajouter progressivement supervision et observabilité.
8.  Étudier les tests de charge, les performances et la consommation
    mémoire.
9.  Continuer à renforcer la qualité de service et la reproductibilité.

------------------------------------------------------------------------

**NetAtlas --- Projet personnel de laboratoire orienté Python ·
PostgreSQL · Flask · Tests · Qualité de service · OPS / DevOps**
