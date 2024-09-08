from medinote.embedding.table_similarity_search import table_similarity_search
from medinote.embedding.embedding_generator import embedding_generator
from medinote.embedding.pgvector_populator import pgvector_populator
from medinote.embedding.vector_search import execute_query
from src.remove_chunks import remove
from medinote import initialize
from fastapi import APIRouter
import pandas as pd
import time
import os


router = APIRouter()

# Initialize base setting and config file
main_config, logger = initialize(
    logger_name=os.path.splitext(os.path.basename(__file__))[0],
    root_path=os.environ.get("ROOT_PATH") or f"{os.path.dirname(__file__)}/..",
)


@router.post('/')
async def main():    
    # Sample note which will be changed later
    try:
        current_time = 1722265922
        list_of_notes = [['1Dysphagia following unspecified cerebral vascular disease I69.991 - Contributing Factors for I69.991 - Dementia -', current_time, current_time, True],['Depression -', current_time, current_time, True],['Tooth Decay', current_time, current_time, True]]
        list_of_notes =  pd.DataFrame(list_of_notes, columns=['text','PID','RID','is_query'])
        list_of_notes.to_parquet('./temp/notes.parquet')
        logger.info(f'Reading notes completed for id {current_time}')
    except Exception as e:
        logger.error(e)

    # Run Embedding Generator
    try:
        embedding_generator()
        time.sleep(0.001)
        logger.info(f'Embedding is done')
    except Exception as e:
        logger.error(e)


    # Make pgvector
    try:
        pgvector_populator()
        time.sleep(0.001)
        logger.info(f'Adding to database is done')
    except Exception as e:
        logger.error(e)


    # Get most similarity
    try:
        table_similarity_search(current_time)
        time.sleep(0.001)
        logger.info(f'Similarity checking is done')
    except Exception as e:
        logger.error(e)


    # Connect to pgvector connection
    query = f"SELECT * FROM note_icd_similarity WHERE rid = %s"
    rows, table_desc = execute_query(query, (str(current_time),), True)

    colnames = [desc[0] for desc in table_desc]
    df = pd.DataFrame(rows, columns=colnames)

    # Group by the specified column
    grouped_df = df.groupby('note_id')
    for g in grouped_df:
        code = g[1].iloc[0]['icd_code']
        note = g[1].iloc[0]['note_text']
        print(code, note)
    # print(grouped_df)
    remove('./temp')

    return {"error": None, "PID" :current_time, "RID":current_time}
