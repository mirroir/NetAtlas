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


-- Tags utilisés par les tests
INSERT INTO tags (id, name, category_id)
VALUES
    (1, 'Marché forain', 1),
    (2, 'Producteurs locaux', 1),
    (3, 'Produits frais', 1);

-- Association des tags au lieu de test
INSERT INTO place_tags (place_id, tag_id)
VALUES
    (1, 1),
    (1, 2),
    (1, 3);

-- Services utilisés par les tests
INSERT INTO services (id, name, description)
VALUES
    (1, 'Parking', 'Stationnement disponible à proximité'),
    (2, 'Accès PMR', 'Accès adapté aux personnes à mobilité réduite'),
    (3, 'Toilettes', 'Toilettes disponibles sur place');

-- Association des services au lieu de test
INSERT INTO place_services (place_id, service_id)
VALUES
    (1, 1),
    (1, 2),
    (1, 3);

INSERT INTO public.users (id, nom, email)
VALUES (1, 'Utilisateur CI', 'ci@netatlas.local');

SELECT pg_catalog.setval(
    'public.users_id_seq',
    (SELECT MAX(id) FROM public.users),
    true
);



