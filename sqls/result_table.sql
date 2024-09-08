DROP TABLE IF EXISTS note_icd_similarity;

CREATE TABLE note_icd_similarity (
    note_id integer,
    pid text,
    rid text,
    note_text text,
    icd_code text,
    icd_id integer,
    distance float8
);