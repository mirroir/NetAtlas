SELECT
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS table_reference,
    ccu.column_name AS colonne_reference
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
     ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage ccu
     ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY';
