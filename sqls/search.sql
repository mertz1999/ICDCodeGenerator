WITH ranked_matches AS (
    SELECT
        icd.id AS icd_id,
        notes.id AS notes_id,
        notes.text As notes_text,
        icd.code As icd_code,
        notes.PID As pid,
        notes.RID As rid,
        icd.embedding <=> notes.embedding AS distance,
        ROW_NUMBER() OVER (PARTITION BY notes.id ORDER BY icd.embedding <=> notes.embedding) AS rank
    FROM
        icd10_v0_table icd,
        request_notes notes
    WHERE
        notes.PID 123145648787987987987
)
SELECT
    notes_id,
    pid,
    rid,
    notes_text,
    icd_code,
    icd_id,
    distance
FROM
    ranked_matches
WHERE
    rank IN (1, 2, 3)
    AND distance < 0.5
ORDER BY
    notes_id, rank;
