-- SELECT * FROM note_icd_similarity
-- where pid='1292109'

-- SELECT note_text, icd_code
-- FROM note_icd_similarity
-- WHERE pid = '1292109'
-- GROUP BY icd_code, note_text;

WITH RankedNotes AS (
    SELECT 
        pid, 
        note_id, 
        distance,`
        note_text,
        icd_code,
        ROW_NUMBER() OVER (PARTITION BY note_id ORDER BY distance) AS rn
    FROM note_icd_similarity
    WHERE pid = '1292109'
)
SELECT note_text, icd_code FROM RankedNotes WHERE rn = 1;
SELECT icd_code FROM RankedNotes WHERE rn = 1;
