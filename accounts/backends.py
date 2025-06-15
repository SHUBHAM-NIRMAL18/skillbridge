from django.contrib.auth.backends import ModelBackend
from .models import User

class EmailBackend(ModelBackend):
    """
    Authenticate using the email field instead of username.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        # here `username` is really the email
        if username is None or password is None:
            return None
        try:
            user = User.objects.get(email__iexact=username)
        except User.DoesNotExist:
            return None
        if user.check_password(password):
            return user
        return None
