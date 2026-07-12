# smart_responder.py
# Fully async version

import asyncio
from groq import AsyncGroq
from vector_cache import cache
from token_optimizer import (
    build_optimized_prompt,
    track_usage,
    get_usage_report,
    is_within_limit
)
from config import GROQ_API_KEY

# Async Groq client
groq_client = AsyncGroq(api_key=GROQ_API_KEY)

# Conversation history per user
conversation_history = {}

# ─────────────────────────────────────────
# PRE-STORED DIRECT RESPONSES
# Zero tokens — instant response
# ─────────────────────────────────────────
DIRECT_RESPONSES = {
    'hello': "👋 Hello! Ask me crypto prices, wallet info, or Web3 questions!",
    'hi': "👋 Hi! How can I help you today?",
    'hey': "👋 Hey! What would you like to know?",
    'who are you': "🤖 I'm an AI + Web3 assistant! I fetch live crypto data and explain blockchain concepts!",
    'what can you do': (
        "I can help with:\n"
        "💰 Live crypto prices\n"
        "👛 Wallet balances\n"
        "📋 Transaction history\n"
        "⛽ Gas fees\n"
        "📚 Web3 explanations\n"
        "💬 General AI chat"
    ),
    'what is blockchain': (
        "⛓️ *Blockchain* is a shared digital "
        "ledger across thousands of computers. "
        "Like a Google Sheet everyone can read "
        "but nobody can edit or delete. "
        "Every transaction is permanent."
    ),
    'what is ethereum': (
        "⟠ *Ethereum* is a programmable "
        "blockchain. Unlike Bitcoin which "
        "only stores value, Ethereum lets "
        "developers build apps and smart "
        "contracts. ETH is its currency."
    ),
    'what is bitcoin': (
        "₿ *Bitcoin* is the first cryptocurrency. "
        "Created in 2009, works without banks. "
        "Only 21 million will ever exist — "
        "making it scarce like digital gold."
    ),
    'what is defi': (
        "🏦 *DeFi* = Decentralized Finance. "
        "Financial services without banks. "
        "Lending, borrowing, trading via "
        "smart contracts automatically. "
        "Examples: Uniswap, Aave, Compound."
    ),
    'what is nft': (
        "🖼️ *NFT* = Non-Fungible Token. "
        "A unique digital asset on blockchain. "
        "Unlike coins, each NFT is one-of-a-kind. "
        "Used for digital art and collectibles."
    ),
    'what is web3': (
        "🌐 *Web3* = blockchain-based internet.\n"
        "Web1: read only\n"
        "Web2: read + write (Facebook, Google)\n"
        "Web3: read + write + OWN your data"
    ),
    'what is smart contract': (
        "📝 *Smart Contract* = self-executing "
        "code on blockchain. Like a vending "
        "machine — conditions met automatically, "
        "result happens. No human needed."
    ),
    'what is gas': (
        "⛽ *Gas* = fee to do anything on "
        "Ethereum. Like a toll booth. "
        "Measured in Gwei. "
        "Higher gas = faster transaction."
    ),
    'what is wallet': (
        "👛 *Crypto Wallet* = your blockchain "
        "identity. Has public address "
        "(like bank account) and private key "
        "(like PIN — NEVER share this!)."
    ),
    'what is staking': (
        "🥩 *Staking* = locking crypto to "
        "validate transactions. In return "
        "you earn rewards like interest. "
        "Used by Ethereum, Solana, Cardano."
    ),
    'what is mining': (
        "⛏️ *Mining* = validating blockchain "
        "transactions using computers. "
        "Miners solve complex puzzles. "
        "Winner earns crypto as reward."
    ),
}

# ─────────────────────────────────────────
# ASYNC: Find direct response
# ─────────────────────────────────────────
def find_direct_response(
    message: str
) -> str:
    """Check for instant pre-stored response"""
    
    msg = message.lower().strip().strip('?!.,')
    
    if msg in DIRECT_RESPONSES:
        return DIRECT_RESPONSES[msg]
    
    for key, response in DIRECT_RESPONSES.items():
        if key in msg:
            return response
    
    return None

# ─────────────────────────────────────────
# ASYNC: Main smart response
# ─────────────────────────────────────────
async def get_smart_response(
    message: str,
    chat_id: int
) -> str:
    """
    3-level optimization:
    Level 1: Direct response   (0 tokens)
    Level 2: Vector cache hit  (0 tokens)
    Level 3: Groq API call     (min tokens)
    """
    
    print(f"\n🧠 Smart: '{message[:50]}'")
    
    # ─────────────────────
    # LEVEL 1: Direct
    # ─────────────────────
    direct = find_direct_response(message)
    if direct:
        print("⚡ Level 1: Direct (0 tokens)")
        track_usage(0, was_cached=True)
        return direct
    
    # ─────────────────────
    # LEVEL 2: Cache
    # Run in executor (uses numpy/sklearn sync)
    # ─────────────────────
    loop = asyncio.get_event_loop()
    
    cached_answer, similarity = (
        await loop.run_in_executor(
            None,
            cache.find_similar,
            message
        )
    )
    
    if cached_answer:
        print(
            f"💾 Level 2: Cache "
            f"({similarity:.3f}, 0 tokens)"
        )
        track_usage(0, was_cached=True)
        return cached_answer
    
    # ─────────────────────
    # LEVEL 3: Groq API
    # ─────────────────────
    if not is_within_limit():
        return (
            "⚠️ Daily limit reached. "
            "Try again tomorrow!"
        )
    
    if chat_id not in conversation_history:
        conversation_history[chat_id] = []
    
    messages, estimated_tokens = (
        build_optimized_prompt(
            message,
            conversation_history[chat_id],
            ""
        )
    )
    
    print(
        f"🤖 Level 3: Groq "
        f"(~{estimated_tokens} tokens)"
    )
    
    try:
        response = await groq_client.chat.completions.create(
            model="llama3-70b-8192",
            messages=messages,
            max_tokens=250,
            temperature=0.7
        )
        
        ai_reply = (
            response.choices[0].message.content
        )
        
        actual_tokens = (
            response.usage.total_tokens
            if hasattr(response, 'usage')
            else estimated_tokens
        )
        
        track_usage(actual_tokens)
        print(f"✅ Used {actual_tokens} tokens")
        
        # Update history
        conversation_history[chat_id].append({
            "role": "user",
            "content": message
        })
        conversation_history[chat_id].append({
            "role": "assistant",
            "content": ai_reply
        })
        
        # Keep last 10 messages only
        if len(
            conversation_history[chat_id]
        ) > 10:
            conversation_history[chat_id] = (
                conversation_history[chat_id][-10:]
            )
        
        # Cache for future
        await loop.run_in_executor(
            None,
            cache.store,
            message,
            ai_reply
        )
        
        return ai_reply
        
    except Exception as e:
        print(f"❌ Groq error: {e}")
        return "❌ AI unavailable. Try again!"

async def clear_user_memory(chat_id: int):
    """Clear user conversation history"""
    if chat_id in conversation_history:
        conversation_history[chat_id] = []
    print(f"🗑️ Cleared: {chat_id}")