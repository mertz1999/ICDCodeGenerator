from medinote.embedding.table_similarity_search import table_similarity_search
from medinote.embedding.embedding_generator import embedding_generator
from medinote.embedding.pgvector_populator import pgvector_populator
from medinote.embedding.vector_search import execute_query
from src.remove_chunks import remove
from src.functions import *
from medinote import initialize
from fastapi import APIRouter
import pandas as pd
import numpy as np
import httpx
import time
import os
import re


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
        current_time = 4564645
        list_of_notes = [['Dysphagia following unspecified cerebral vascular disease I69.991 - Contributing Factors for I69.991 - Dementia -', current_time, current_time, True],['Depression -', current_time, current_time, True],['Tooth Decay', current_time, current_time, True]]
        # list_of_notes = [['Tooth Decay', current_time, current_time, True]]
        list_of_notes =  pd.DataFrame(list_of_notes, columns=['text','PID','RID','is_query'])
        list_of_notes.to_parquet('./temp/notes.parquet')
        logger.info(f'Reading notes completed for id {current_time}')
    except Exception as e:
        logger.error(e)
        return {'error':'problem in json parsing'}

    # Run Embedding Generator
    try:
        embedding_generator()
        time.sleep(0.001)
        logger.info(f'Embedding is done')
    except Exception as e:
        logger.error(e)
        return {'error':'problem in Embedding'}

    # Make pgvector
    try: 
        pgvector_populator()
        time.sleep(0.001)
        logger.info(f'Adding to database is done')
    except Exception as e:
        logger.error(e)
        return {'error':'problem in Adding to database'}


    # Get most similarity
    try:
        table_similarity_search(current_time)
        time.sleep(0.001)
        logger.info(f'Similarity checking is done')
    except Exception as e:
        logger.error(e)
        return {'error': 'similarity search problem'}

    # Exract the codes from database
    try:
        query = f"SELECT * FROM note_icd_similarity WHERE rid = %s"
        rows, table_desc = execute_query(query, (str(current_time),), True)

        colnames = [desc[0] for desc in table_desc]
        df = pd.DataFrame(rows, columns=colnames)

        # Group by the specified column
        grouped_df = df.groupby('note_id')
        codes = []
        for g in grouped_df:
            code = g[1].iloc[0]['icd_code']
            note = g[1].iloc[0]['note_text']
            dist = g[1].iloc[0]['distance']
            print(code, note, dist)
            codes.append((note, code, dist))
    except Exception as e:
        codes = []
        logger.error(e)
        return {'error':'failed to fetch most similar ICD codes'}

    best_codes = []
    very_good_codes = []
    # Split codes based on their distance and some other rules
    try:
        for code_ in codes:
            if code_[-1] < 0.35 and ('K2' not in code_[1]) and ('R13' not in code_[1]) and  (code_[1] != 'R63.30') and (re.search('I69\.\d91', code_[1]) is None) and (code_[1] != 'I69.821'):
                very_good_codes.append(code_[1])
                if code_[1] in best_codes:
                    best_codes.remove(code_[1])
            else:
                if code_[1] not in very_good_codes:
                    best_codes.append(code_[1])


        if 'I69.821' in best_codes:
            best_codes[best_codes.index('I69.821')] = 'I69.891'
        if 'I69.821' in very_good_codes:    
            very_good_codes[very_good_codes.index('I69.821')] = 'I69.891'
        
        very_good_codes = list(np.unique(very_good_codes))
        best_codes = list(np.unique(best_codes))
    except Exception as e:
        logger.error(e)
        return {'error':'splitting problem'}

    try:
        uns = lambda x : x.replace('UNSPECIFIED', ' ').replace('Unspecified',' ').replace('unspecified',' ').replace('UNSP', ' ')
        code_def = pd.read_csv('./inc/icd10_selected.csv')
        list_of_code_with_def = ''
        for code in np.unique(best_codes):
            s = code_def[code_def.code == code]
            list_of_code_with_def += f'{code} : {uns(str(s.text.iloc[0]))}' + '\n'

        print(list_of_code_with_def)
    except Exception as e:
        logger.error('Error to make codes with def')
        return {'error':'codes definition error'}

    # Refining Stage
    try:
        with open('./prompts/refine-prompt.txt', 'r') as file:
            template_content = file.read()

        info = {
            'predicted_codes': list_of_code_with_def,
            'diags': '\n'.join(list(np.unique(list_of_notes.text))),
            'ome': '\n'.join([]),
            'mbss': '\n'.join([]),
            'raf' : '\n'.join([]),
            'chief': '\n'.join([])
        }

        formatted_content = template_content.format(**info)
        with open(f'./temp/prompt_{current_time}.txt', 'w') as file:
            file.write(formatted_content)
        logger.info(f'Prompt is saved in ./temp/{current_time}')

        # Pass it to refining LLM
        res = final_codes(formatted_content)
        # print(res)

        # extract
        for split_ in res.split('\n'):
            if 'step 1 : ' in split_:
                r13_codes = split_[9:].replace(" ", "").split(',')
                print(r13_codes)
            if 'step 2 : ' in split_:
                i69_codes = split_[9:].replace(" ", "").split(',')
                print(i69_codes)
            if 'step 3 : ' in split_:
                k2_codes = split_[9:].replace(" ", "").split(',')
                print(k2_codes)
            if 'step 4 : ' in split_:
                need_to_rm = split_[9:].replace(" ", "").split(',')
                print(need_to_rm)
    except Exception as e:
        logger.error(e)
        return {'error':'refining failed'}


    # Generate final codes after refining
    try:
        final_codes_ = i69_codes+r13_codes+['R63.30']+k2_codes
        for code_ in np.unique(best_codes):
            if ('R13' not in code_) and ('K2' not in code_) and (code_ != 'R63.30') and (re.search("I69\.\d91", code_) is None) and (code_ not in need_to_rm):
                final_codes_.append(code_)

        final_codes_ += very_good_codes
        print('final codes', final_codes_)
    except Exception as e:
        logger.error(e)
        return {'error':'failed to generate final list of codes'}

    try:
        final_codes_ = filter_none(final_codes_)
        async with httpx.AsyncClient() as client:
            codes_get = ','.join(final_codes_)
            print("$$$$$$$$ ",final_codes_, codes_get)
            base_url = 'http://localhost:8000/api/v1/sorting/'+codes_get
            response = await client.get(base_url)
            print(response.json())
            if response.status_code == 200:
                final_codes_ = response.json()['sortedCodes'].split(',')
            else:
                return {'error':f'failed to sort {response.status_code}'}

    except Exception as e:
        logger.error(e)
        return {'error':'sorting failed'}
    
    remove('./temp')
    return {"error": None, "PID" :current_time, "RID":current_time, "codes":final_codes_}
