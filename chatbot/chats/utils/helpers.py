# utils/helpers.py
import re
import json
from .embeddings import generate_embedding  
from django.db import connection
import django.utils.timezone as timezone
from ..models import ChatDetails, ChatHistory1
import uuid
from django.db.models import F
from pgvector.django import CosineDistance
from django.db import connection

def generate_chat_title(first_message):
    if not first_message or not first_message.strip():
        return "New Chat"
    first_message = first_message.strip()
    first_message = re.sub(r'(?i)\b(hi|hello|hey|greetings|dear)\b', '', first_message)
    cleaned = re.sub(r'[^\w\s]', '', first_message).strip()
    words = [word for word in cleaned.split() if len(word) > 1]
    short_title = " ".join(words[:10])
    return short_title.title() if short_title else "New Chat"


def save_message_with_embedding(chat, role, text):
    """
    Saves a ChatHistory1 message and its embedding.
    Returns the saved object.
    """
    from ..models import ChatHistory1  # avoid circular import at module level

    # create message first
    message_obj = ChatHistory1.objects.create(
        chat=chat,
        role=role,
        message=text,
        timestamp=timezone.now()
    )

    try:
        embedding = generate_embedding(text)
        message_obj.embedding = embedding
        message_obj.save(update_fields=["embedding"])
    except Exception as e:
        print(f"Embedding generation failed for role={role}:", e)

    return message_obj



def get_or_create_chat(user, chat_id, first_message):
    """
    Given a user and optional chat_id, returns an existing chat or creates a new one.
    Always returns (chat_object, chat_id).
    """
    if not chat_id:
        chat_id = str(uuid.uuid4())
        chat_title = generate_chat_title(first_message)
        chat = ChatDetails.objects.create(
            chat_id=chat_id,
            title=chat_title,
            created_at=timezone.now(),
            modified_at=timezone.now(),
            user=user
        )
    else:
        chat, created = ChatDetails.objects.get_or_create(
            chat_id=chat_id,
            defaults={
                "title": generate_chat_title(first_message),
                "created_at": timezone.now(),
                "modified_at": timezone.now(),
                "user": user
            }
        )
    return chat, chat_id


def get_similar_from_other_chats(query_vector, current_chat_id, top_n=5):
    similar = (
        ChatHistory1.objects
        .exclude(chat__chat_id=current_chat_id)
        .annotate(distance=CosineDistance(F('embedding'), query_vector))
        .order_by('distance')[:top_n]
    )
    
    # Format into list of dicts compatible with your memory
    return [
        {"role": msg.role, "content": msg.message}
        for msg in similar
    ]



# def get_relevant_documents(embedding, match_count=5):
#     # Convert the list of floats into a PostgreSQL vector string: '(0.12, -0.34, ...)'
#     vector_literal = "[" + ",".join(str(f) for f in embedding) + "]"

#     with connection.cursor() as cursor:
#         cursor.execute(
#             "SELECT content FROM match_documents(%s::vector, %s, '{}')",
#             [vector_literal, match_count]
#         )
#         return [row[0] for row in cursor.fetchall()]

def parse_metadata(metadata):
    """Helper to handle metadata whether it's a string or already a dict"""
    if isinstance(metadata, str):
        try:
            return json.loads(metadata)
        except json.JSONDecodeError:
            return {}
    elif isinstance(metadata, dict):
        return metadata
    return {}

# import json
# from django.db import connection

def get_relevant_documents(embedding, match_count=5, filters=None):
    """
    Get relevant documents using the match_documents function
    Args:
        embedding: List[float] - The query embedding vector
        match_count: int - Number of results to return
        filters: dict - Metadata filters (e.g., {"case": "XYZ"})
    Returns:
        List[dict] - Each containing id, content, metadata, and similarity
    """
    filter_json = json.dumps(filters) if filters else '{}'
    
    with connection.cursor() as cursor:
        try:
            # Execute the function with proper type casting
            cursor.execute(
                """
                SELECT * FROM match_documents(
                    %s::vector(384),
                    %s,
                    %s::jsonb
                )
                """,
                [embedding, match_count, filter_json]
            )
            
            # Process results with proper type handling
            results = []
            for row in cursor.fetchall():
                metadata = row[2]
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                    except json.JSONDecodeError:
                        metadata = {}
                
                results.append({
                    "id": row[0],
                    "content": row[1],
                    "metadata": metadata,
                    "similarity": float(row[3])
                })
            
            return results
            
        except Exception as e:
            print(f"Error in get_relevant_documents: {str(e)}")
            return []