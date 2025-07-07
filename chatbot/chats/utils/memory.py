import numpy as np
from ..models import ChatHistory1,ChatDetails
from .embeddings import generate_embedding
from .helpers import get_similar_from_other_chats

GROQ_TOKEN_LIMIT = 5000

# --- Short-Term Memory ---
def get_short_term_memory(chat_id, limit=10):
    """Get last N messages from the current chat"""
    try:
        response = (
            ChatHistory1.objects.filter(chat__chat_id = chat_id).order_by('-timestamp')[:limit]
        )
        return list(reversed([
            {"role": row.role, "content": row.message}
            for row in response
        ]))
    except Exception as e:
        print("Short Term memory Error: ", e)
        return []

# --- Long Term Memory ---
def rough_token_count(text):
    words = text.split()
    return int(len(words) * 1.33)  # 1.33 tokens per word

def estimate_tokens_from_messages(messages):
    total_tokens = 0
    for msg in messages:
        total_tokens += rough_token_count(msg["content"])
    return total_tokens


def get_complete_long_term_memory(user_l,current_chat_id, prompt= None):
    memory = []

    # 1. All messages from current chat
    current_chat_qs = ChatHistory1.objects.filter(chat__chat_id=current_chat_id).order_by("timestamp")
    current_chat_messages = [
        {"role": msg.role, "content": msg.message}
        for msg in current_chat_qs
    ]
    token_size = estimate_tokens_from_messages(current_chat_messages)

    print("Token size :",token_size)

    if token_size > GROQ_TOKEN_LIMIT:
        chat_meta = ChatDetails.objects.get(chat_id=current_chat_id)
        memory.append({
            "role": "system",
            "content": f"Summary of current chat: '{chat_meta.summary}'"
        })
    else:
        memory += current_chat_messages

    # # 2. Similar messages from other chats
    # query_vector = generate_embedding(prompt)
    # memory += get_similar_from_other_chats(query_vector, current_chat_id)

    # # 3. Summary of other chats
    # summaries = ChatDetails.objects.filter(user=user_l)\
    # .exclude(chat_id=current_chat_id)\
    # .order_by("modified_at")

    # summary_texts = [f"'{s1.summary}'" for s1 in summaries]
    # summary_blob = "Previously chats on: " + "; ".join(summary_texts)

    # memory.append({
    #     "role": "system",
    #     "content": summary_blob
    # })


    return memory

