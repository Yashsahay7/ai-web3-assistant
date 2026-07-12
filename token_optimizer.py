# token_optimizer.py
# Reduces token usage before sending to Groq
# Tracks token usage
# Compresses prompts intelligently

import tiktoken
import re
from datetime import datetime, date

# Token usage tracker
token_usage = {
    'total_today': 0,
    'total_all_time': 0,
    'api_calls_today': 0,
    'cache_hits_today': 0,
    'date': str(date.today()),
    'tokens_saved': 0
}

# Daily token limit
# Free Groq tier = 14400 tokens/minute
# Set daily limit to be safe
DAILY_TOKEN_LIMIT = 50000

def count_tokens(text: str) -> int:
    """
    Count tokens in text
    Uses cl100k_base (GPT-4 tokenizer)
    Close enough for Groq estimation
    """
    try:
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except:
        # Rough estimate: 1 token ≈ 4 chars
        return len(text) // 4

def compress_message(message: str) -> str:
    """
    Compresses user message to use fewer tokens
    While keeping meaning intact
    """
    
    # Remove excessive whitespace
    message = ' '.join(message.split())
    
    # Remove unnecessary filler words
    filler_words = [
        'please', 'could you', 'would you',
        'can you', 'i want to know',
        'i would like to know',
        'tell me about', 'explain to me',
        'i am curious about', 'hey',
        'hello', 'hi there', 'kindly'
    ]
    
    msg_lower = message.lower()
    for filler in filler_words:
        msg_lower = msg_lower.replace(filler, '')
    
    # Clean up and return
    compressed = ' '.join(msg_lower.split())
    
    original_tokens = count_tokens(message)
    compressed_tokens = count_tokens(compressed)
    saved = original_tokens - compressed_tokens
    
    if saved > 0:
        token_usage['tokens_saved'] += saved
        print(
            f"✂️ Compressed: "
            f"{original_tokens} → "
            f"{compressed_tokens} tokens "
            f"(saved {saved})"
        )
    
    return compressed

def build_optimized_prompt(
    message: str,
    conversation_history: list,
    system_prompt: str
) -> tuple:
    """
    Builds prompt using minimum tokens
    
    Strategy:
    1. Compress the message
    2. Limit conversation history
    3. Trim system prompt
    4. Stay under token limit
    
    Returns (messages_list, token_count)
    """
    
    MAX_HISTORY_TOKENS = 500
    MAX_RESPONSE_TOKENS = 300
    
    # Compress user message
    compressed_msg = compress_message(message)
    
    # Build minimal system prompt
    minimal_system = (
        "You are a Web3/crypto AI assistant. "
        "Be concise. Under 150 words per response. "
        "No financial advice."
    )
    
    # Calculate base token count
    base_tokens = (
        count_tokens(minimal_system)
        + count_tokens(compressed_msg)
        + MAX_RESPONSE_TOKENS
    )
    
    # Add conversation history
    # Start from most recent
    # Add until we hit token limit
    history_tokens = 0
    selected_history = []
    
    for msg in reversed(conversation_history[-10:]):
        msg_tokens = count_tokens(
            msg.get('content', '')
        )
        
        if (history_tokens + msg_tokens
                > MAX_HISTORY_TOKENS):
            break
        
        selected_history.insert(0, msg)
        history_tokens += msg_tokens
    
    # Build final messages
    messages = [
        {
            "role": "system",
            "content": minimal_system
        },
        *selected_history,
        {
            "role": "user",
            "content": compressed_msg
        }
    ]
    
    total_tokens = base_tokens + history_tokens
    
    return messages, total_tokens

def track_usage(
    tokens_used: int,
    was_cached: bool = False
):
    """Track API token usage"""
    
    # Reset daily counter if new day
    today = str(date.today())
    if token_usage['date'] != today:
        token_usage['total_today'] = 0
        token_usage['api_calls_today'] = 0
        token_usage['cache_hits_today'] = 0
        token_usage['date'] = today
    
    if was_cached:
        token_usage['cache_hits_today'] += 1
    else:
        token_usage['total_today'] += tokens_used
        token_usage['total_all_time'] += tokens_used
        token_usage['api_calls_today'] += 1

def is_within_limit() -> bool:
    """Check if under daily token limit"""
    return (
        token_usage['total_today']
        < DAILY_TOKEN_LIMIT
    )

def get_usage_report() -> str:
    """Get token usage statistics"""
    return (
        f"📊 *Token Usage Report*\n\n"
        f"Today:\n"
        f"├ Tokens used: `{token_usage['total_today']:,}`\n"
        f"├ API calls: `{token_usage['api_calls_today']}`\n"
        f"├ Cache hits: `{token_usage['cache_hits_today']}`\n"
        f"└ Tokens saved: `{token_usage['tokens_saved']:,}`\n\n"
        f"All time:\n"
        f"└ Total tokens: `{token_usage['total_all_time']:,}`\n\n"
        f"Daily limit: `{DAILY_TOKEN_LIMIT:,}`\n"
        f"Remaining: "
        f"`{DAILY_TOKEN_LIMIT - token_usage['total_today']:,}`"
    )
