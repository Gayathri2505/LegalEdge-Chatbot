import os
from groq import Groq
from typing import Generator
from dotenv import load_dotenv

load_dotenv()

# -------------------- GROQ --------------------

# Configuration constants
GROQ_MODEL = "llama3-8b-8192"  
MAX_TOKENS = 1000
TEMPERATURE = 0.7

# Initialize groq client using API Key
def initialize_groq_client():
    api_key = os.getenv('GROQ_API_KEY')
    if not api_key:
        return None
    try:
        client = Groq(api_key=api_key)
        return client
    except Exception as e:
        return None

# Receive Responses from Groq
def get_groq_response(client: Groq, messages: list) -> Generator[str, None, None]:
    try:
        stream = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            stream=True
        )
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except Exception as e:
        yield f"Error Occured: {str(e)}"

# Generate a summary of chats
def summarize_chat(messages):
    """Generate a semantic summary for a chat"""
    system_prompt = "Summarize the following conversation in 4-5 sentences. " \
    "Capture the topic and identify what the user prefer."

    formatted = "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in messages])
    chat_input = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": formatted}
    ]

    client = initialize_groq_client()
    summary = ""
    for chunk in get_groq_response(client, chat_input):
        summary += chunk
    return summary.strip()