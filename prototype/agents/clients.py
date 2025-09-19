""" Initialize Clients for LLMs and Singleton-like methods
    such that every method can access them for better performance """

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
