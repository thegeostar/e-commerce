from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_superuser:
            messages.warning(request, "You are not authorized to access this page")
            return redirect('/user/sign-in/')

        return view_func(request, *args, **kwargs)

    return wrapper
