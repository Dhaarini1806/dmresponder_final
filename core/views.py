from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import ContactFormSubmission
from .serializers import ContactFormSubmissionSerializer

def landing_page(request):
    """Landing page view"""
    return render(request, 'landing.html')

def login_view(request):
    """Login view"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('dashboard')
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Invalid username or password.")
    form = AuthenticationForm()
    return render(request, 'registration/login.html', {'form': form})

def signup_view(request):
    """Signup view"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registration successful.")
            return redirect('dashboard')
        else:
            for error in form.errors.values():
                messages.error(request, error)
    form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})

def logout_view(request):
    """Logout view"""
    logout(request)
    messages.info(request, "You have successfully logged out.")
    return redirect('landing_page')

def privacy_policy(request):
    """Privacy policy page"""
    return render(request, 'privacy_policy.html')

def terms_of_service(request):
    """Terms of service page"""
    return render(request, 'terms_of_service.html')

def data_deletion(request):
    """Data deletion page"""
    return render(request, 'data_deletion.html')

class ContactFormViewSet(viewsets.ModelViewSet):
    """ViewSet for contact form submissions"""
    serializer_class = ContactFormSubmissionSerializer
    permission_classes = []
    
    def get_queryset(self):
        return ContactFormSubmission.objects.all()
    
    def create(self, request, *args, **kwargs):
        """Handle contact form submission"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
