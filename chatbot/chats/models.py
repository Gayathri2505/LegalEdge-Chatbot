from django.contrib.auth.models import AbstractUser
from django.db import models
from pgvector.django import VectorField
from django.conf import settings

class ChatDetails(models.Model):
    chat_id = models.CharField(primary_key=True, max_length=255)
    title = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    modified_at = models.DateTimeField(null=True, blank=True)
    summary = models.TextField(null=True, blank=True)
    last_summarized = models.DateTimeField(null=True, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL ,
        db_column='user',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='chats'
    )

    class Meta:
        db_table = 'ChatDetails'
        managed = False   


class ChatHistory1(models.Model):
    id = models.BigAutoField(primary_key=True)
    chat = models.ForeignKey(ChatDetails, on_delete=models.CASCADE, db_column='chat_id', null=True, blank=True)
    role = models.CharField(max_length=255)
    message = models.CharField(max_length=1000, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_memory = models.BooleanField(default=True, null=True, blank=True)
    embedding = VectorField(dimensions=1536, null=True, blank=True)

    class Meta:
        db_table = 'ChatHistory1'
        managed = False   


class Document(models.Model):
    id = models.BigAutoField(primary_key=True)
    content = models.TextField()
    metadata = models.JSONField()
    embedding = VectorField(dimensions=384)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'documents'
        managed = False 