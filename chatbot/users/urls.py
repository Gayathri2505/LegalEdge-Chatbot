from django.urls import path
from .views import logout_view, home_view,auth_view

urlpatterns = [
    path('auth/', auth_view, name='auth'),
    path('logout/', logout_view, name='logout'),
    path('', home_view, name='home')
]
