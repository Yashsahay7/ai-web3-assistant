# test_router.py
# Updated test file

import sys
sys.path.append('.')

# Only import route_message
# get_intent no longer exists
from bot_router import route_message

print("Testing routing...\n")

tests = [
    "What is ETH worth?",
    "What are gas fees right now?",
    "How is the market today?",
    "Bitcoin price",
    "What is a smart contract?",
    "Solana price",
    "Show me BTC value",
]

for message in tests:
    print(f"{'─'*40}")
    print(f"📨 Message: '{message}'")
    response = route_message(message, 12345)
    print(f"✅ Response: {response[:100]}...")
    print()