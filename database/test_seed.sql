-- ============================================================
-- NetAtlas - Jeu de données minimal pour les tests automatisés
-- Utilisé uniquement par l'environnement de test / CI
-- ============================================================

-- Pays
INSERT INTO pays
    (id, name, iso2, iso3, continent, capital, currency, language, population)
VALUES
    (1, 'France', 'FR', 'FRA', 'Europe', 'Paris', 'EUR', 'Français', 68000000);

-- Région
INSERT INTO regions
    (id, country_id, name, territoire_id)
VALUES
    (1, 1, 'La Réunion', NULL);

-- Ville utilisée par les tests
INSERT INTO villes
    (id, region_id, name, latitude, longitude, population)
VALUES
    (1, 1, 'Saint-Pierre', -21.3393, 55.4781, 85000);

-- Catégorie minimale
INSERT INTO categories
    (id, name, description)
VALUES
    (1, 'Marché', 'Catégorie utilisée pour les tests automatisés');

-- Lieu utilisé par les tests
INSERT INTO places
    (
        id,
        ville_id,
        category_id,
        name,
        description,
        address,
        latitude,
        longitude,
        phone,
        email,
        website,
        is_active
    )
VALUES
    (
        1,
        1,
        1,
        'Marché de Saint-Pierre',
        'Lieu utilisé pour les tests automatisés NetAtlas',
        'Saint-Pierre',
        -21.3393,
        55.4781,
        NULL,
        NULL,
        NULL,
        TRUE
    );
