# 🌍 NetAtlas

[![NetAtlas Tests](https://github.com/mirroir/NetAtlas/actions/workflows/tests.yml/badge.svg)](https://github.com/mirroir/NetAtlas/actions/workflows/tests.yml)

> Laboratoire Python / PostgreSQL orienté recherche, tests automatisés,
> qualité de service et pratiques DevOps.

Le projet met en œuvre une application CLI connectée à PostgreSQL, un moteur de recherche multi-critères, une batterie de *38 tests automatisés avec pytest* et une *intégration continue avec GitHub Actions* permettant d'exécuter automatiquement les contrôles du projet.

L'objectif est de faire évoluer progressivement NetAtlas vers une chaîne complète inspirée des pratiques *OPS / DevOps* : développement, gestion des données, tests, contrôle qualité, automatisation, intégration continue et déploiement.

## 🎯 Objectifs du projet

- Concevoir et administrer une base PostgreSQL structurée
- Développer une application Python connectée à la base
- Construire un moteur de recherche multi-critères
- Mettre en place des tests automatisés
- Contrôler la qualité de fonctionnement de l'application
- Sécuriser les données de configuration et les secrets
- Faire évoluer progressivement le projet vers une chaîne DevOps

## 🏗️ Architecture technique

NetAtlas est organisé en plusieurs couches afin de séparer les responsabilités :

- *PostgreSQL* : stockage et structuration des données
- *Python* : logique applicative et accès à la base de données
- *Interface CLI* : navigation et interrogation des données depuis le terminal
- *pytest* : validation automatisée du comportement de l'application
- *Shell / Bash* : contrôle global de l'état du projet

### Organisation simplifiée

```text
NetAtlas/
|-- database/        Scripts SQL et diagnostics
|-- python/          Application Python
|   |-- database.py  Accès PostgreSQL et requêtes
|   |-- main.py      Boucle principale
|   `-- menu.py      Interface utilisateur
|-- scripts/         Scripts de contrôle et d'automatisation
|-- tests/           Tests automatisés
|-- .gitignore       Protection des fichiers locaux et sensibles
`-- README.md        Documentation publique du projet
```

## 🔎 Moteur de recherche

NetAtlas dispose d'un moteur de recherche global capable d'interroger plusieurs
sources de données, notamment les lieux, les villes et les catégories.

La recherche combine :

- ILIKE pour une recherche insensible à la casse
- pg_trgm et similarity() pour améliorer la tolérance des recherches
- un score de pertinence pour ordonner les résultats
- une limitation du nombre de résultats retournés

Cette approche permet d'aller au-delà d'une simple correspondance exacte et
constitue une première étape vers un moteur de recherche plus tolérant.

## 🧪 Tests automatisés & qualité de service

La qualité de fonctionnement constitue un axe important du projet NetAtlas.

Une batterie de tests automatisés avec *pytest* permet de contrôler les
différentes fonctions de l'application et les interactions avec la base de données.

Le projet dispose actuellement de :

- *38 tests automatisés*
- tests des fonctions Python
- tests du moteur de recherche
- tests de l'environnement
- tests des permissions PostgreSQL
- validation des interactions entre l'application et la base de données

Un script de contrôle global permet également d'exécuter les vérifications
principales du projet :


````bash 
./scripts/check_netatlas.sh
````
Les contrôles sont également intégrés à *GitHub Actions* afin d'exécuter automatiquement la chaîne de tests dans un environnement CI à chaque évolution du projet.

Le badge affiché en haut de ce README permet de visualiser directement l'état de la dernière exécution de la CI.

L'objectif est de disposer progressivement d'un contrôle reproductible permettant
de détecter rapidement une régression avant une évolution ou un déploiement.

## 🔐 Sécurité

Les données locales et sensibles ne sont pas versionnées dans le dépôt public.

Le fichier .gitignore permet notamment d'exclure :

- les fichiers d'environnement contenant des secrets
- l'environnement virtuel Python
- les caches Python et pytest
- les fichiers de configuration locaux
- les données de test qui ne doivent pas être publiées

Aucun mot de passe ou token d'authentification n'est destiné à être stocké
directement dans le code source.

## ⚙️ Démarche DevOps

NetAtlas est également utilisé comme support d'apprentissage pour faire évoluer
une application vers une approche plus proche des pratiques d'exploitation
et de production.

La démarche DevOps de NetAtlas s'appuie désormais sur :

- la gestion des versions avec *Git*
- l'automatisation des contrôles avec *Bash / Shell*
- les tests automatisés avec *pytest*
- l'intégration continue avec *GitHub Actions*
- le contrôle de l'état de la CI via le badge du projet

Les prochaines évolutions viseront notamment :

- l'évolution de la chaîne *CI/CD*
- l'expérimentation avec *GitLab et Jenkins*
- le déploiement d'une interface Web
- l'ajout de mécanismes de supervision
- le renforcement continu de la sécurité et de la qualité de service

## 🛠️ Technologies

- Python
- PostgreSQL
- SQL
- pytest
- Bash / Shell
- Git
- GitHub
- Linux

## 🚧 État du projet

NetAtlas est un projet en évolution continue.

La version actuelle comprend notamment :

- une base PostgreSQL fonctionnelle
- une application Python en ligne de commande
- une navigation par menu
- une recherche par villes et lieux
- une recherche globale multi-critères
- une recherche tolérante avec pg_trgm
- une batterie de tests automatisés
- un script de contrôle global
- une intégration continue opérationnelle avec *GitHub Actions*
- l'exécution automatisée des *38 tests* dans la CI
- un dépôt Git public sécurisé

## 🗺️ Roadmap

Les prochaines étapes prévues sont :

1. Consolider la documentation technique
2. Étendre progressivement la couverture des tests automatisés
3. Faire évoluer la CI GitHub Actions vers une chaîne CI/CD complète
4. Expérimenter une chaîne DevOps avec GitLab et Jenkins
5. Créer une interface Web pour NetAtlas
6. Ajouter des mécanismes de supervision et d'observabilité
7. Continuer à renforcer les contrôles de sécurité et de qualité de service

---

*NetAtlas* — Projet personnel de laboratoire orienté
*Python · PostgreSQL · Tests · Qualité de service · DevOps*
