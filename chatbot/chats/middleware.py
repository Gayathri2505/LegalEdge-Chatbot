import os
from django.conf import settings
from chats.knowledge_base.ingest import embed_folder

ran_once = False

class KnowledgeSyncMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        global ran_once
        if not ran_once:
            kb_path = os.path.join(settings.BASE_DIR, 'chats', 'knowledge_base', 'documents')
            try:
                embed_folder(kb_path)
                print("✅ Knowledge base synced (via middleware)")
            except Exception as e:
                print("❌ Middleware KB ingestion failed:", e)
            ran_once = True

        return self.get_response(request)
