from django.shortcuts import render
import uuid
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
import json
from .utils.memory import get_short_term_memory, get_complete_long_term_memory
from .utils.groq import initialize_groq_client, get_groq_response, summarize_chat
from .utils.helpers import generate_chat_title,save_message_with_embedding,get_or_create_chat
from django.utils import timezone
from .models import ChatDetails, ChatHistory1
from .utils.embeddings import generate_embedding
from datetime import timedelta
from .utils.helpers import get_relevant_documents, parse_metadata
from django.views.decorators.csrf import csrf_exempt

@login_required
def chat_view(request):
    return render(request, 'chat.html', {'user': request.user,  'hide_navbar': True})


@login_required
def new_chat(request):
    if request.method == "POST":
        # Just return a placeholder acknowledgment or even skip this entirely if frontend handles it
        return JsonResponse({"status": "ready_for_new_chat"})
    return JsonResponse({"error": "Invalid request"}, status=400)


@login_required
def chatbot_response(request):
    if request.method == "POST":
        user_message = request.POST.get("message")
        chat_id = request.POST.get("chat_id")  # frontend should send chat_id if known

        chat, chat_id = get_or_create_chat(request.user, chat_id, user_message)

        user_msg_obj = save_message_with_embedding(chat,"user",user_message)

        query_embedding = generate_embedding(user_message)

        short_mem = get_short_term_memory(chat.chat_id)
        short_mem = short_mem[-6:]

        long_mem = get_complete_long_term_memory(request.user,chat.chat_id)


        # print("--"*50)
        # print("Long term: \n",long_mem)
        # print("--"*50)
        # print("Short term: \n",short_mem)


        # get bot response
        client = initialize_groq_client()
        if not client:
            return JsonResponse({"response": "❌ Failed to initialize Groq client."})
        
        INSTRUCTIONS = """
        You are a Legal Edge assistant provide precise, authoritative answers based on the documents.

        CRITICAL INSTRUCTIONS:
        1. Maintain strict legal accuracy - never speculate beyond the documents
        2. When a question references previous context (e.g., "the above case", "that ruling"), 
        interpret it within the ongoing conversation by:
            a. Identifying the referenced case/concept
            b. Explicitly acknowledging the connection
            c. Maintaining consistent interpretation
        3. For follow-up questions without explicit case names:
            - Check the conversation history for relevant cases
            - Assume continuation of the most recent relevant case
        4. When uncertain, ask clarifying questions

        Structure your response as follows:
            - Begin with a direct answer to the legal question
            - Provide supporting analysis based on the legal information
            - Present facts and legal points clearly without document citations in the main text
            - Maintain formal legal writing style throughout
        
        """
        kb_chunks = get_relevant_documents(query_embedding, match_count=10)

        #kb_context = "\n\n".join(["- " + chunk for chunk in kb_chunks])
        
        kb_context = "\n\n".join([
            f"📄 Document {i+1} (From: {parse_metadata(chunk['metadata']).get('file_name', 'unknown')}):\n"
            f"{chunk['content']}\n"
            f"Similarity: {chunk['similarity']:.2%}"
            for i, chunk in enumerate(kb_chunks)
        ])

        full_instructions = (
            INSTRUCTIONS + 
            f"\n\nCONVERSATION CONTEXT:\n{short_mem}\n\n" +
            f"DOCUMENT CONTEXT:\n{kb_context}"
        )


        messages = [
            {"role": "system", "content": full_instructions}
        ]

        # Add long-term memory if exists (optimized format)
        if long_mem:
            # Consolidated long-term context formatting
            long_term_context = (
                "Relevant Case History and Context:\n"
                "---------------------------------\n"
                + "\n".join(
                    f"{m['role'].upper()}: {m['content']}\n"
                    f"{'-'*40}" 
                    for m in long_mem[-4:]  # Last 2 exchanges
                )
            )
            messages.append({"role": "system", "content": long_term_context})

        # Add short-term memory (last few messages)
        short_mem = get_short_term_memory(chat.chat_id)[-4:]  # Last 2 exchanges
        messages.extend(short_mem)

        
        total_chars = sum(len(m["content"]) for m in messages)
        print("Prompt size in chars:", total_chars)

        response_text = ""
        for chunk in get_groq_response(client, messages):
            response_text += chunk

        bot_msg_object = save_message_with_embedding(chat,"assistant",response_text)

        ChatDetails.objects.filter(chat_id=chat.chat_id).update(
            modified_at = timezone.now()
        )

        if chat.title == "New Chat":
            chat.title = generate_chat_title(user_message)
            chat.save()

        # Try generating and saving a summary if needed
        if not chat.summary or timezone.make_aware(chat.last_summarized) < timezone.now()-timedelta(days=1):
            messages_qs = ChatHistory1.objects.filter(chat=chat).order_by("timestamp")
            if messages_qs.count() > 5:
                message_dicts = [
                    {"role": m.role, "content": m.message}
                    for m in messages_qs
                ]
                try:
                    summary_text = summarize_chat(message_dicts)
                    chat.summary = summary_text
                    #chat.save()

                    ChatDetails.objects.filter(chat_id=chat.chat_id).update(
                        summary = summary_text,
                        last_summarized = timezone.now().isoformat()
                    )

                except Exception as e:
                    print("Summary generation failed:", e)


        return JsonResponse({
            "response": response_text,
            "chat_id": chat_id  # return to frontend so it can reuse next time
        })
    
@login_required
def get_user_chats(request):
    chats = ChatDetails.objects.filter(user=request.user).order_by('-modified_at')
    chat_list = [
        {"chat_id": chat.chat_id, "title": chat.title, "created_at": chat.created_at.strftime('%Y-%m-%d %H:%M'), "modified_at": chat.modified_at.strftime('%Y-%m-%d %H:%M')}
        for chat in chats
    ]
    return JsonResponse({"chats": chat_list})


@login_required
def update_chat_title(request):
    if request.method == "POST":
        data = json.loads(request.body)
        chat_id = data.get("chat_id")
        first_message = data.get("message", "")

        if not chat_id:
            return JsonResponse({"error": "chat_id is required"}, status=400)

        try:
            chat = ChatDetails.objects.get(chat_id=chat_id, user=request.user)
            if chat.title == "New Chat":
                chat.title = generate_chat_title(first_message)
                chat.save()
            return JsonResponse({"title": chat.title})
        except ChatDetails.DoesNotExist:
            return JsonResponse({"error": "Chat not found"}, status=404)


@login_required
def get_chat_messages(request, chat_id):
    try:
        print("Chatid", chat_id)
        chat = ChatDetails.objects.get(chat_id=chat_id, user=request.user)
        messages = ChatHistory1.objects.filter(chat=chat).order_by("timestamp")
        history = [
            {"role": msg.role, "message": msg.message, "timestamp": msg.timestamp.strftime("%Y-%m-%d %H:%M")}
            for msg in messages
        ]
        return JsonResponse({"messages": history})
    except ChatDetails.DoesNotExist:
        return JsonResponse({"error": "Chat not found."}, status=404)


@login_required
def generate_summary(request):
    if request.method == "POST":
        data = json.loads(request.body)
        chat_id = data.get("chat_id")

        try:
            chat = ChatDetails.objects.get(chat_id=chat_id, user=request.user)
        except ChatDetails.DoesNotExist:
            return JsonResponse({"error": "Chat not found"}, status=404)

        if chat.summary:
            return JsonResponse({"summary": chat.summary})  # already exists

        messages = ChatHistory1.objects.filter(chat=chat).order_by("timestamp")
        if messages.count() < 6:
            return JsonResponse({"error": "Not enough messages to summarize"}, status=400)

        formatted = [
            {"role": msg.role, "content": msg.message}
            for msg in messages
        ]

        summary = summarize_chat(formatted)
        chat.summary = summary
        chat.save()

        return JsonResponse({"summary": summary})