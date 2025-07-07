from django.urls import path
from . import views

urlpatterns = [
    path('', views.chat_view, name='chat'),
    path('chat/chatbot-response/', views.chatbot_response, name='chatbot-response'),
    path('chat/get-user-chats/', views.get_user_chats, name='get-user-chats'),
    path('chat/update-chat-title/', views.update_chat_title, name='update_chat_title'),
    path('chat/new-chat/', views.new_chat, name='new-chat'),
    path("chat/get-messages/<str:chat_id>/", views.get_chat_messages, name="get_chat_messages"),
    path("chat/generate-summary/", views.generate_summary, name="generate_summary"),

]