# 🌍 NetAtlas

> Laboratoire Python / PostgreSQL orienté recherche, tests automatisés,
> qualité de service et pratiques DevOps.

NetAtlas est un projet personnel conçu comme un laboratoire technique permettant
de mettre en pratique différentes compétences autour de l'exploitation,
des bases de données et de l'automatisation.

Le projet repose actuellement sur une application Python connectée à PostgreSQL
et propose notamment un moteur de recherche global permettant d'interroger
plusieurs types de données.

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

Les prochaines évolutions visent notamment :

- l'automatisation des contrôles
- l'intégration continue
- la gestion des versions avec Git
- la mise en place d'une chaîne CI/CD
- l'expérimentation avec GitLab et Jenkins
- le déploiement d'une interface Web
- l'amélioration de la supervision et de la qualité de service

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
- un dépôt Git public sécurisé

## 🗺️ Roadmap

Les prochaines étapes prévues sont :

1. Consolider la documentation technique
2. Automatiser davantage les tests
3. Mettre en place une première chaîne CI/CD
4. Expérimenter GitLab et Jenkins
5. Créer une interface Web pour NetAtlas
6. Ajouter des mécanismes de supervision
7. Continuer à renforcer les contrôles de sécurité

---

*NetAtlas* — Projet personnel de laboratoire orienté
*Python · PostgreSQL · Tests · Qualité de service · DevOps*
