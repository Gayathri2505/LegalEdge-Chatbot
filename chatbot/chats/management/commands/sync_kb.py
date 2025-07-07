from django.core.management.base import BaseCommand
from chats.knowledge_base.ingest import embed_folder
from django.conf import settings
import os

class Command(BaseCommand):
    help = 'Ingest and embed PDF documents into Supabase'

    def handle(self, *args, **kwargs):
        kb_path = os.path.join(settings.BASE_DIR, 'chats', 'knowledge_base', 'documents')
        self.stdout.write(f"📚 Ingesting KB from {kb_path}")
        try:
            embed_folder(kb_path)
            self.stdout.write(self.style.SUCCESS("✅ Knowledge base synced successfully."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ KB ingestion failed: {e}"))
