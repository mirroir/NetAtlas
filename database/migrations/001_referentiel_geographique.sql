-- NetAtlas
-- Migration 001 : référentiel géographique
--
-- Parcours utilisateur :
-- Pays -> Territoire -> Ville -> Lieu
--
-- Les régions Nord / Est / Sud / Ouest restent
-- un niveau géographique interne.

BEGIN;

-- Création du secteur Sud uniquement s'il n'existe pas déjà.
INSERT INTO regions (name, country_id, territoire_id)
SELECT
    'Sud',
    pa.id,
    tr.id
FROM pays pa
JOIN territoires tr
    ON LOWER(tr.name) = LOWER('La Réunion')
WHERE LOWER(pa.name) = LOWER('France')
  AND NOT EXISTS (
      SELECT 1
      FROM regions r
      WHERE LOWER(r.name) = LOWER('Sud')
        AND r.country_id = pa.id
        AND r.territoire_id = tr.id
  );

-- Saint-Pierre doit appartenir au secteur Sud.
UPDATE villes
SET region_id = (
    SELECT r.id
    FROM regions r
    JOIN pays pa
        ON r.country_id = pa.id
    JOIN territoires tr
        ON r.territoire_id = tr.id
    WHERE LOWER(r.name) = LOWER('Sud')
      AND LOWER(pa.name) = LOWER('France')
      AND LOWER(tr.name) = LOWER('La Réunion')
)
WHERE LOWER(name) = LOWER('Saint-Pierre');

COMMIT;
