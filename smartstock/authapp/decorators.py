from django.shortcuts import redirect,render
from django.contrib import messages

def role_required(allowed_roles=[]):
    def decorator(view_func):
        def wrapper_func(request, *args, **kwargs):
            if request.user.is_authenticated:
                if request.user.role in allowed_roles:
                    return view_func(request, *args, **kwargs)
                else:
                    messages.error(request, "You are not authorized to view this page.")
                    return redirect('login')
            else:
                return redirect('login')
        return wrapper_func
    return decorator
