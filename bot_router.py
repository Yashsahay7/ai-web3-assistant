# bot_router.py
# Fully async version

from web3_handler import (
    get_wallet_balance,
    get_transactions,
    get_gas_fees,
    get_market_overview
)
from smart_responder import get_smart_response
from crypto_scraper import get_any_crypto_price

# ─────────────────────────────────────────
# KEYWORD LISTS
# ─────────────────────────────────────────
GAS_KEYWORDS = [
    'gas', 'gas fee', 'gas fees',
    'network fee', 'transaction fee', 'gwei'
]

MARKET_KEYWORDS = [
    'market overview', 'market update',
    'all coins', 'top coins',
    'crypto market', 'overview',
    'market summary', 'multiple prices'
]

PRICE_KEYWORDS = [
    'price', 'worth', 'value', 'cost',
    'how much', 'rate', 'trading at',
    'current price', 'what is price'
]

TRANSACTION_KEYWORDS = [
    'transaction', 'transactions', 'history',
    'transfers', 'sent', 'received', 'activity'
]

RISK_KEYWORDS = [
    'risk', 'safe', 'analyze',
    'suspicious', 'legit', 'scam'
]

# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────
def has_keyword(
    message: str, keywords: list
) -> bool:
    msg = message.lower()
    return any(kw in msg for kw in keywords)

def find_wallet_address(message: str) -> str:
    for word in message.split():
        clean = word.strip('.,!?()[]{}:;\'"')
        if (clean.startswith('0x')
                and len(clean) == 42):
            return clean
    return None

# ─────────────────────────────────────────
# FORMAT FUNCTIONS
# ─────────────────────────────────────────
def format_price(data: dict) -> str:
    if not data['success']:
        return f"❌ {data['error']}"
    
    change_24h = data.get('change_24h', 0) or 0
    change_7d = data.get('change_7d', 0) or 0
    e1 = "📈" if change_24h > 0 else "📉"
    e2 = "📈" if change_7d > 0 else "📉"
    
    r = (
        f"💹 *{data['name']} ({data['symbol']})*\n\n"
        f"💵 USD: `${data.get('price_usd', 0):,}`\n"
        f"🇮🇳 INR: `₹{data.get('price_inr', 0):,}`\n\n"
        f"{e1} 24h: `{change_24h:+.2f}%`\n"
    )
    if change_7d != 0:
        r += f"{e2} 7d: `{change_7d:+.2f}%`\n"
    
    high = data.get('high_24h', 0)
    low = data.get('low_24h', 0)
    if high and low:
        r += (
            f"\n📊 High: `${high:,}`\n"
            f"📊 Low: `${low:,}`\n"
        )
    
    mcap = data.get('market_cap', 0)
    rank = data.get('rank', 'N/A')
    if mcap:
        r += f"\n🏦 Cap: `${mcap:,.0f}`\n"
    if rank and rank != 'N/A':
        r += f"🏆 Rank: `#{rank}`"
    
    return r

def format_balance(data: dict) -> str:
    if not data['success']:
        return f"❌ {data['error']}"
    return (
        f"👛 *Wallet Balance*\n\n"
        f"📍 `{data['address'][:16]}...`\n"
        f"⟠ ETH: `{data['eth']}`\n"
        f"💵 USD: `${data['usd']:,}`\n"
        f"📊 ETH Price: `${data['eth_price']:,}`"
    )

def format_transactions(data: dict) -> str:
    if not data['success']:
        return f"❌ {data['error']}"
    if not data['txns']:
        return "📭 No transactions found"
    
    text = (
        f"📋 *Recent Transactions*\n"
        f"`{data['address']}`\n\n"
    )
    for i, tx in enumerate(data['txns'], 1):
        arrow = (
            "⬇️ IN" if tx['direction'] == 'IN'
            else "⬆️ OUT"
        )
        text += (
            f"{i}. {arrow}\n"
            f"   `{tx['eth']} ETH` ≈ `${tx['usd']}`\n"
            f"   {tx['status']}\n\n"
        )
    return text

def format_gas(data: dict) -> str:
    if not data['success']:
        return f"❌ {data['error']}"
    return (
        f"⛽ *Gas Fees*\n\n"
        f"{data['status']}\n\n"
        f"🐢 Slow: `{data['slow']} Gwei`\n"
        f"🚶 Normal: `{data['gwei']} Gwei`\n"
        f"🚀 Fast: `{data['fast']} Gwei`\n\n"
        f"💸 Transfer: `~${data['transfer_usd']}`"
    )

def format_market(data: dict) -> str:
    if not data['success']:
        return f"❌ {data['error']}"
    text = "📊 *Crypto Market*\n\n"
    for symbol, info in data['coins'].items():
        e = "📈" if info['change'] > 0 else "📉"
        text += (
            f"{e} *{symbol}*: "
            f"`${info['price']:,}` "
            f"({info['change']:+.2f}%)\n"
        )
    return text

# ─────────────────────────────────────────
# MAIN ASYNC ROUTER
# ─────────────────────────────────────────
async def route_message(
    message: str,
    chat_id: int
) -> str:
    """
    Fully async message router
    All functions awaited properly
    """
    
    msg = message.lower().strip()
    print(f"\n🔍 Routing: '{msg}'")
    
    # ─────────────────────
    # GAS FEES
    # ─────────────────────
    if has_keyword(msg, GAS_KEYWORDS):
        print("→ GAS_FEES")
        data = await get_gas_fees()
        return format_gas(data)
    
    # ─────────────────────
    # MARKET OVERVIEW
    # ─────────────────────
    if has_keyword(msg, MARKET_KEYWORDS):
        print("→ MARKET_OVERVIEW")
        data = await get_market_overview()
        return format_market(data)
    
    # ─────────────────────
    # WALLET OPERATIONS
    # ─────────────────────
    if '0x' in msg:
        address = find_wallet_address(msg)
        if address:
            if has_keyword(
                msg, TRANSACTION_KEYWORDS
            ):
                print("→ TRANSACTIONS")
                data = await get_transactions(
                    address
                )
                return format_transactions(data)
            
            elif has_keyword(msg, RISK_KEYWORDS):
                print("→ WALLET_RISK")
                # Run both concurrently
                balance, txns = await asyncio.gather(
                    get_wallet_balance(address),
                    get_transactions(address, 10)
                )
                prompt = (
                    f"Analyze wallet risk:\n"
                    f"Balance: {balance}\n"
                    f"Txns: {txns}\n"
                    f"Give LOW/MEDIUM/HIGH risk "
                    f"in under 100 words."
                )
                return await get_smart_response(
                    prompt, chat_id
                )
            
            else:
                print("→ WALLET_BALANCE")
                data = await get_wallet_balance(
                    address
                )
                return format_balance(data)
    
    # ─────────────────────
    # CRYPTO PRICE
    # ─────────────────────
    if has_keyword(msg, PRICE_KEYWORDS):
        print("→ CRYPTO_PRICE")
        data = await get_any_crypto_price(message)
        if data['success']:
            return format_price(data)
        return await get_smart_response(
            message, chat_id
        )
    
    # Short message — might be coin name
    if len(msg.split()) <= 3:
        data = await get_any_crypto_price(message)
        if data['success']:
            print("→ CRYPTO_PRICE (short)")
            return format_price(data)
    
    # ─────────────────────
    # DEFAULT: AI
    # ─────────────────────
    print("→ AI")
    return await get_smart_response(
        message, chat_id
    )