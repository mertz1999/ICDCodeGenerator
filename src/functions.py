from openai import OpenAI
import shutil
import os 
import requests
import json
from scipy.stats import spearmanr
import httpx

def recreate_folder(path):
    # Check if the folder exists
    if os.path.exists(path):
        # Remove the folder and all its contents
        shutil.rmtree(path)
        print(f"Folder '{path}' has been removed.")
    
    os.makedirs(path)



def final_codes(prompt):
  client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

  
  response = client.chat.completions.create(
  model="gpt-4o-mini",
  messages=[
      {
        "role" : "system",
        "content" : "you are a medical code analyzer. based on the information answer each step and explain it. In all stage please use the code description that I provided for you."
      },
      {
      "role": "user",
      "content": prompt
      }
  ],
  temperature=0.7,  
  max_tokens=2048,
#   top_p=0.9,
  )

  gpt_result = response.choices[0].message.content

  return gpt_result


def llama_v31(user_prompt):
    # API endpoint and headers
    url = 'http://80.188.223.202:11350/v1/chat/completions'
    headers = {'Content-Type': 'application/json'}

    # Prepare the payload
    payload = {
        "model": "llama-3.1:8B",
        "messages": [
            {"role": "system", "content": "you are a medical code analyzer. based on the information answer each step and explain it. In all stage please use the code description that I provided for you."},
            {"role": "user", "content": user_prompt}
        ]
    }

    # Send the POST request
    response = requests.post(url, headers=headers, data=json.dumps(payload))

    # Print the response
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    else:
        return 'nothing'


def hier_metrics(your_list, correct_list):
    # all codes
    common_codes       = set(your_list) & set(correct_list)
    rho1 = 0

    # common codes
    your_list          = [i for i in your_list if i in common_codes]
    correct_list       = [i for i in correct_list if i in common_codes]

    ranks_your_list    = [your_list.index(code) + 1 for code in correct_list]
    ranks_correct_list = [correct_list.index(code) + 1 for code in correct_list]
    rho2, _            = spearmanr(ranks_your_list, ranks_correct_list)

    return rho1, rho2



async def SortDxCodes(codes):
    async with httpx.AsyncClient() as client:
        # response_data = response.json()

    # Define the base URL of your FastAPI server
        base_url = 'http://localhost:8000/api/v1/sorting/'
        response = await client.get(base_url)

    # # Define the list of codes as a comma-separated string
    # codes = ','.join(codes)
    # # Send a GET request with the codes as a query parameter
    # response = requests.get(base_url+codes)
    # Print the response
        if response.status_code == 200:
            return {response.json()['sortedCodes'].split(',')}
        else:
            return {'error':response.status_code}


uns = lambda x : x.replace('UNSPECIFIED', ' ').replace('Unspecified',' ').replace('unspecified',' ').replace('UNSP', ' ')



def filter_none(final_codes_):
    # Define the items to remove
    items_to_remove = {None, 'None', 'NONE', 'none', 'non', 'null', 'NULL'}
    
    # Create a new list excluding the items to remove
    filtered_list = [item for item in final_codes_ if item not in items_to_remove]
    
    return filtered_list
