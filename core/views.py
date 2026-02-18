from django.shortcuts import render

def dashboard(request):
    template_data = {'title': 'Dashboard'}
    return render(request, 'core/dashboard.html', {'template_data': template_data})

def notifications(request):
    template_data = {'title': 'Notifications'}
    return render(request, 'core/notifications.html', {'template_data': template_data})

def profile(request):
    template_data = {'title': 'Profile'}
    return render(request, 'core/profile.html', {'template_data': template_data})

# Create your views here.
