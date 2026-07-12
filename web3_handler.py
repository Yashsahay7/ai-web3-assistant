# web3_handler.py
# Fully async version

import asyncio
import aiohttp
from web3 import Web3
from config import ALCHEMY_URL, ETHERSCAN_API_KEY

# Web3 connection stays sync
# (Web3.py does not support async natively)
# But we run it in executor to avoid blocking
w3 = Web3(Web3.HTTPProvider(ALCHEMY_URL))

# ─────────────────────────────────────────
# ASYNC HTTP SESSION
# Reuse single session for all requests
# Much faster than creating new each time
# ─────────────────────────────────────────
async def fetch_json(
    url: str,
    session: aiohttp.ClientSession
) -> dict:
    """
    Async HTTP GET request
    Returns JSON response
    """
    try:
        async with session.get(
            url,
            timeout=aiohttp.ClientTimeout(total=10)
        ) as response:
            return await response.json()
    except Exception as e:
        print(f"❌ HTTP error: {e}")
        return {}

# ─────────────────────────────────────────
# VALIDATORS
# ─────────────────────────────────────────
def is_valid_address(address: str) -> bool:
    if not address:
        return False
    if not address.startswith('0x'):
        return False
    if len(address) != 42:
        return False
    return True

# ─────────────────────────────────────────
# ASYNC: Get ETH price
# ─────────────────────────────────────────
async def get_eth_price() -> float:
    """Get live ETH price asynchronously"""
    try:
        async with aiohttp.ClientSession() as session:
            url = (
                "https://api.coingecko.com"
                "/api/v3/simple/price"
                "?ids=ethereum&vs_currencies=usd"
            )
            data = await fetch_json(url, session)
            return data.get(
                'ethereum', {}
            ).get('usd', 3000.0)
    except:
        return 3000.0

# ─────────────────────────────────────────
# ASYNC: Get any token price
# ─────────────────────────────────────────
async def get_token_price(token: str) -> dict:
    """Get price of any token asynchronously"""
    
    token_map = {
        'btc': 'bitcoin',
        'eth': 'ethereum',
        'sol': 'solana',
        'bnb': 'binancecoin',
        'matic': 'matic-network',
        'polygon': 'matic-network',
        'doge': 'dogecoin',
        'link': 'chainlink',
        'ada': 'cardano',
        'dot': 'polkadot',
        'avax': 'avalanche-2',
        'xrp': 'ripple',
        'shib': 'shiba-inu',
        'uni': 'uniswap',
        'aave': 'aave',
        'ltc': 'litecoin',
        'atom': 'cosmos',
        'near': 'near',
        'algo': 'algorand'
    }
    
    token_id = token.lower().strip()
    if token_id in token_map:
        token_id = token_map[token_id]
    
    try:
        async with aiohttp.ClientSession() as session:
            url = (
                "https://api.coingecko.com"
                "/api/v3/simple/price"
                f"?ids={token_id}"
                "&vs_currencies=usd,inr"
                "&include_24hr_change=true"
                "&include_market_cap=true"
            )
            data = await fetch_json(url, session)
            
            if token_id not in data:
                return {
                    'success': False,
                    'error': f'Token not found: {token}'
                }
            
            info = data[token_id]
            return {
                'success': True,
                'name': token.upper(),
                'usd': info.get('usd', 0),
                'inr': info.get('inr', 0),
                'change_24h': round(
                    info.get('usd_24h_change', 0) or 0,
                    2
                ),
                'market_cap': info.get(
                    'usd_market_cap', 0
                ) or 0
            }
    except Exception as e:
        return {'success': False, 'error': str(e)}

# ─────────────────────────────────────────
# ASYNC: Get wallet balance
# Runs Web3 in executor to avoid blocking
# ─────────────────────────────────────────
async def get_wallet_balance(address: str) -> dict:
    """Get ETH balance asynchronously"""
    
    if not is_valid_address(address):
        return {
            'success': False,
            'error': 'Invalid wallet address'
        }
    
    try:
        # Run blocking Web3 call in thread executor
        # This prevents blocking the event loop
        loop = asyncio.get_event_loop()
        
        checksum = w3.to_checksum_address(address)
        
        balance_wei = await loop.run_in_executor(
            None,
            w3.eth.get_balance,
            checksum
        )
        
        balance_eth = float(
            w3.from_wei(balance_wei, 'ether')
        )
        
        eth_price = await get_eth_price()
        
        return {
            'success': True,
            'address': address,
            'eth': round(balance_eth, 6),
            'usd': round(balance_eth * eth_price, 2),
            'eth_price': eth_price
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

# ─────────────────────────────────────────
# ASYNC: Get transactions
# ─────────────────────────────────────────
async def get_transactions(
    address: str,
    limit: int = 5
) -> dict:
    """Get wallet transactions asynchronously"""
    
    if not is_valid_address(address):
        return {
            'success': False,
            'error': 'Invalid wallet address'
        }
    
    try:
        async with aiohttp.ClientSession() as session:
            url = (
                "https://api.etherscan.io/api"
                "?module=account"
                "&action=txlist"
                f"&address={address}"
                "&startblock=0"
                "&endblock=99999999"
                "&page=1"
                f"&offset={limit}"
                "&sort=desc"
                f"&apikey={ETHERSCAN_API_KEY}"
            )
            
            data = await fetch_json(url, session)
            
            if data.get('status') != '1':
                return {
                    'success': True,
                    'address': address,
                    'txns': [],
                    'message': 'No transactions found'
                }
            
            eth_price = await get_eth_price()
            txns = []
            
            for tx in data.get('result', [])[:limit]:
                val_eth = float(tx['value']) / 1e18
                direction = (
                    'IN' if tx['to'].lower()
                    == address.lower()
                    else 'OUT'
                )
                txns.append({
                    'direction': direction,
                    'eth': round(val_eth, 6),
                    'usd': round(
                        val_eth * eth_price, 2
                    ),
                    'from': tx['from'][:10] + '...',
                    'to': tx['to'][:10] + '...',
                    'status': (
                        '✅' if tx.get(
                            'txreceipt_status'
                        ) == '1' else '❌'
                    )
                })
            
            return {
                'success': True,
                'address': address[:10] + '...',
                'txns': txns
            }
            
    except Exception as e:
        return {'success': False, 'error': str(e)}

# ─────────────────────────────────────────
# ASYNC: Get gas fees
# ─────────────────────────────────────────
async def get_gas_fees() -> dict:
    """Get current gas fees asynchronously"""
    
    try:
        loop = asyncio.get_event_loop()
        
        # Run blocking Web3 call in executor
        gas_wei = await loop.run_in_executor(
            None,
            lambda: w3.eth.gas_price
        )
        
        gas_gwei = float(
            w3.from_wei(gas_wei, 'gwei')
        )
        
        eth_price = await get_eth_price()
        transfer_usd = (
            gas_gwei * 21000 / 1e9 * eth_price
        )
        
        if gas_gwei > 50:
            status = '🔴 Congested'
        elif gas_gwei > 20:
            status = '🟡 Normal'
        else:
            status = '🟢 Low'
        
        return {
            'success': True,
            'gwei': round(gas_gwei, 2),
            'slow': round(gas_gwei * 0.8, 2),
            'fast': round(gas_gwei * 1.3, 2),
            'transfer_usd': round(transfer_usd, 4),
            'status': status
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

# ─────────────────────────────────────────
# ASYNC: Get market overview
# ─────────────────────────────────────────
async def get_market_overview() -> dict:
    """Get market overview asynchronously"""
    
    try:
        async with aiohttp.ClientSession() as session:
            url = (
                "https://api.coingecko.com"
                "/api/v3/coins/markets"
                "?vs_currency=usd"
                "&ids=bitcoin,ethereum,solana,"
                "binancecoin,matic-network,chainlink"
                "&order=market_cap_desc"
                "&per_page=6"
                "&page=1"
                "&sparkline=false"
                "&price_change_percentage=24h"
            )
            
            data = await fetch_json(url, session)
            
            coins = {}
            for coin in data:
                symbol = coin['symbol'].upper()
                change = coin.get(
                    'price_change_percentage_24h'
                ) or 0.0
                price = coin.get(
                    'current_price'
                ) or 0.0
                
                coins[symbol] = {
                    'price': price,
                    'change': round(float(change), 2)
                }
            
            return {'success': True, 'coins': coins}
            
    except Exception as e:
        return {'success': False, 'error': str(e)}