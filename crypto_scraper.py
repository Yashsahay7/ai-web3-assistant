# crypto_scraper.py
# Fully async version

import asyncio
import aiohttp
import json
from groq import AsyncGroq
from config import (
    FIRECRAWL_API_KEY,
    GROQ_API_KEY
)

# Async Groq client
groq_client = AsyncGroq(api_key=GROQ_API_KEY)

# ─────────────────────────────────────────
# ASYNC: Search and get price
# ─────────────────────────────────────────
async def search_and_get_price(
    coin_name: str
) -> dict:
    """Search CoinGecko for any coin"""
    
    print(f"🔍 Searching: {coin_name}")
    
    try:
        async with aiohttp.ClientSession() as session:
            
            # Step 1: Search for coin ID
            search_url = (
                "https://api.coingecko.com"
                "/api/v3/search"
                f"?query={coin_name}"
            )
            
            async with session.get(
                search_url,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as r:
                search_data = await r.json()
            
            coins = search_data.get('coins', [])
            
            if not coins:
                return {
                    'success': False,
                    'error': f'Not found: {coin_name}'
                }
            
            coin_id = coins[0]['id']
            coin_symbol = coins[0]['symbol'].upper()
            coin_full_name = coins[0]['name']
            
            print(f"✅ Found: {coin_full_name}")
            
            # Step 2: Get price data
            price_url = (
                "https://api.coingecko.com"
                "/api/v3/coins/markets"
                "?vs_currency=usd"
                f"&ids={coin_id}"
                "&order=market_cap_desc"
                "&per_page=1"
                "&page=1"
                "&sparkline=false"
                "&price_change_percentage=24h,7d"
            )
            
            # Step 3: Get INR price
            inr_url = (
                "https://api.coingecko.com"
                "/api/v3/simple/price"
                f"?ids={coin_id}"
                "&vs_currencies=inr"
            )
            
            # Run both requests concurrently
            price_task = session.get(
                price_url,
                timeout=aiohttp.ClientTimeout(
                    total=10
                )
            )
            inr_task = session.get(
                inr_url,
                timeout=aiohttp.ClientTimeout(
                    total=10
                )
            )
            
            # Wait for both simultaneously
            async with price_task as pr, \
                       inr_task as ir:
                price_data = await pr.json()
                inr_data = await ir.json()
            
            if not price_data:
                return {
                    'success': False,
                    'error': 'No price data'
                }
            
            coin = price_data[0]
            
            # Safe extraction
            current_price = (
                coin.get('current_price') or 0
            )
            change_24h = (
                coin.get(
                    'price_change_percentage_24h'
                ) or 0
            )
            change_7d = (
                coin.get(
                    'price_change_percentage_7d'
                    '_in_currency'
                ) or 0
            )
            market_cap = coin.get('market_cap') or 0
            volume_24h = coin.get('total_volume') or 0
            high_24h = coin.get('high_24h') or 0
            low_24h = coin.get('low_24h') or 0
            rank = coin.get('market_cap_rank', 'N/A')
            
            inr_price = (
                inr_data.get(coin_id, {})
                .get('inr', current_price * 85)
            )
            
            return {
                'success': True,
                'name': coin_full_name,
                'symbol': coin_symbol,
                'price_usd': current_price,
                'price_inr': inr_price,
                'change_24h': round(
                    float(change_24h), 2
                ),
                'change_7d': round(
                    float(change_7d), 2
                ),
                'market_cap': market_cap,
                'volume_24h': volume_24h,
                'high_24h': high_24h,
                'low_24h': low_24h,
                'rank': rank,
                'source': 'CoinGecko API'
            }
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return {'success': False, 'error': str(e)}

# ─────────────────────────────────────────
# ASYNC: Extract coin name using AI
# ─────────────────────────────────────────
async def extract_coin_name(
    message: str
) -> str:
    """Extract coin name from message using AI"""
    
    prompt = f"""
    Extract cryptocurrency name from: "{message}"
    
    Return ONLY the coin name or symbol.
    Examples:
    "stellar price" → stellar
    "how much is zcash" → zcash
    "ETH price" → ethereum
    "aster coin" → astar
    If no coin: return none
    """
    
    try:
        response = await groq_client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{
                "role": "user",
                "content": prompt
            }],
            max_tokens=15,
            temperature=0
        )
        
        coin = (
            response.choices[0]
            .message.content
            .strip()
            .lower()
        )
        
        return None if coin == 'none' else coin
        
    except:
        return None

# ─────────────────────────────────────────
# ASYNC: Main price getter
# ─────────────────────────────────────────
async def get_any_crypto_price(
    user_message: str
) -> dict:
    """
    Get price of any cryptocurrency
    from any user message
    """
    
    # Extract coin name
    coin_name = await extract_coin_name(
        user_message
    )
    
    if not coin_name:
        return {
            'success': False,
            'error': 'Could not identify cryptocurrency'
        }
    
    print(f"📊 Getting price for: {coin_name}")
    
    return await search_and_get_price(coin_name)