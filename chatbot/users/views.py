from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import CustomUserCreationForm, CustomLoginForm

def auth_view(request):
    register_form = CustomUserCreationForm()
    login_form = CustomLoginForm(request, data=request.POST or None)

    if request.method == 'POST':
        form_type = request.POST.get('form_type')

        if form_type == 'signup':
            register_form = CustomUserCreationForm(request.POST)
            if register_form.is_valid():
                user = register_form.save()
                login(request, user)
                messages.success(request, 'Successfully signed up and logged in!')
                return redirect('home')
            else:
                messages.error(request, 'Signup failed. Please correct the errors below.')

        elif form_type == 'login':
            login_form = CustomLoginForm(request, data=request.POST)
            if login_form.is_valid():
                user = login_form.get_user()
                login(request, user)
                messages.success(request, 'Successfully signed in!')
                return redirect('chat')
            else: 
                messages.error(request, 'Invalid username or password.')

    return render(request, 'signin_signup.html', {
        'form': register_form,
        'login_form': login_form
    })


def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('auth')


def home_view(request):
    return render(request, 'home.html')
