# llm_handler.py
# Now just imports from smart_responder
# All optimization handled there

from smart_responder import (
    get_smart_response,
    clear_user_memory
)

def get_ai_response(
    message: str,
    chat_id: int
) -> str:
    """
    Wrapper function
    Routes to smart responder
    """
    return get_smart_response(message, chat_id)