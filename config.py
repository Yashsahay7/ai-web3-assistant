# config.py
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
ALCHEMY_URL = os.getenv('ALCHEMY_URL')
ETHERSCAN_API_KEY = os.getenv('ETHERSCAN_API_KEY')
FIRECRAWL_API_KEY = os.getenv('FIRECRAWL_API_KEY')

missing = []
if not TELEGRAM_TOKEN:
    missing.append('TELEGRAM_BOT_TOKEN')
if not GROQ_API_KEY:
    missing.append('GROQ_API_KEY')
if not ALCHEMY_URL:
    missing.append('ALCHEMY_URL')
if not ETHERSCAN_API_KEY:
    missing.append('ETHERSCAN_API_KEY')
if not FIRECRAWL_API_KEY:
    missing.append('FIRECRAWL_API_KEY')

if missing:
    print(f"⚠️ Missing keys: {missing}")

print("✅ Config loaded successfully")