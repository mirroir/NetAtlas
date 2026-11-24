# NetAtlas — Qualité et intégrité des migrations PostgreSQL

## 1. Présentation

NetAtlas applique une démarche d'amélioration continue
orientée vers la qualité, la sécurité, l'intégrité des données
et la maîtrise des évolutions applicatives.

La gestion des migrations PostgreSQL s'inscrit dans
cette démarche.

## 2. Principes techniques

- Versionnement des migrations SQL.
- Contrôle des empreintes SHA-256.
- Séparation des environnements.
- Préservation de l'historique des migrations.
- Validation des évolutions par des tests automatisés.
- Contrôle des permissions PostgreSQL.
- Traçabilité des opérations de déploiement.
- Prévention des régressions applicatives.

## 3. Référence historique

Audit réalisé le 24 novembre 2026.

Commit applicatif de référence : 2795a36.

| Indicateur | Résultat historique |
|---|---:|
| Migrations PostgreSQL examinées | 22 |
| Empreintes SHA-256 conformes | 22 |
| Tests automatisés réussis | 937 |
| Couverture Python mesurée | 100 % |
| Instructions Python mesurées | 1326 |
| Instructions non couvertes | 0 |

Ces résultats correspondent au périmètre audité
et à la configuration de test utilisée.

Ils ne constituent pas une certification exhaustive
de sécurité.

## 4. Contrôle d'intégrité

Le fichier migrations_sha256.txt contient les empreintes
historiques des migrations SQL 001 à 022.

Depuis la racine du projet :

```bash
sha256sum --check --strict docs/audit/migrations_sha256.txt
```

Les migrations historiques doivent conserver leur intégrité.

Toute divergence doit faire l'objet d'une investigation.

Le manifeste ne constitue pas une signature cryptographique
indépendante du dépôt Git.

## 5. Validation applicative

Depuis la racine du projet :

```bash
bash scripts/check_netatlas.sh
```

Cette procédure permet de vérifier la qualité du code,
les tests applicatifs et la couverture mesurée.

## 6. Gestion des évolutions

Les évolutions structurelles de PostgreSQL doivent être
réalisées par de nouvelles migrations versionnées.

Les migrations historiques ne doivent pas être modifiées
pour masquer une divergence ou une correction ultérieure.

La démarche de gestion des migrations privilégie
la reproductibilité, la validation préalable,
la traçabilité et la maîtrise des changements.

## 7. Confidentialité

Les informations opérationnelles sensibles, les procédures
d'administration détaillées et les observations internes
de sécurité ne sont pas publiées dans ce répertoire public.

## 8. Amélioration continue

NetAtlas poursuit une démarche progressive de consolidation
de son architecture, de ses contrôles automatisés et de
ses mécanismes de sécurité.

La qualité constitue une exigence permanente du projet.
