"""Test chat endpoint"""
import sys, json
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv('.env')

from openai import OpenAI
from app.config import get_settings

settings = get_settings()
print(f"Base URL: {settings.ai_api_base_url}")
print(f"Model: {settings.ai_model_name}")
print(f"API Key prefix: {settings.ai_api_key[:10]}...")

# Test direct API call
try:
    client = OpenAI(base_url=settings.ai_api_base_url, api_key=settings.ai_api_key)
    resp = client.chat.completions.create(
        model=settings.ai_model_name,
        messages=[{"role": "user", "content": "你好，说一句话"}],
        max_tokens=50,
    )
    print(f"API OK: {resp.choices[0].message.content}")
except Exception as e:
    print(f"API Error: {type(e).__name__}: {e}")