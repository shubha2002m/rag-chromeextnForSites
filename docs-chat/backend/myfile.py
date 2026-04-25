#this file is for testing the genai client and api key setup. You can run this file to verify that your API key is working correctly and that you can make requests to the Gemini API. OR use postman or curl

from google import genai
import os
from dotenv import load_dotenv

load_dotenv()#reads env variables from .env

# The client gets the API key from the environment variable `GEMINI_API_KEY`automatically
client = genai.Client()

response = client.models.generate_content(
    model="gemini-3-flash-preview", contents="Explain thermodynamics in few wrods"
)
print(response.text)