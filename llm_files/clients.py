""" Initialize Clients for LLMs and Singleton-like methods
    such that every method can access them for better performance """

import requests
import json
import os
from dotenv import load_dotenv

import openai
from xai_sdk import Client

load_dotenv()

# Initialize clients once at module level
openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
xai_client = Client(api_key=os.getenv("XAI_API_KEY"))

def get_openai_client():
    """ Returns OpenAI client """
    return openai_client

def get_xai_client():
    """ Returns xAI client """
    return xai_client

def get_apertus_client(prompt, model):
    """ Returns Apertus client """
    url = "https://api.publicai.co/v1/chat/completions"

    payload = json.dumps({
        "model": f"swiss-ai/{model}",
        "messages": [
            {
                "role": "system",
                "content": "You are a highly intelligent AI assistant helping Swiss citizens to freely form an opinion on their own by adding context to their questions and tasks."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    })
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {os.getenv("PUBLICAI_API_KEY")}'
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    data = json.loads(response.text)

    return data["choices"][0]["message"]["content"]

title = "Umweltschutzinitiative"
prompt = f"""Given the classes Environment, Social Affairs and Education, Economy and Finance, Foreign and Security Policy, Infrastructure and Transportation, Health and Other, classify the following popular vote in Switzerland by its title: {title}. Only output the class label, no reasoning at all."""
model = "apertus-8b-instruct"
print(get_apertus_client(prompt, model))