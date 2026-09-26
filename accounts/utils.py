from .models import User, UserRole

DEFAULT_ADMIN_USERNAME = 'admin2'
DEFAULT_ADMIN_EMAIL = 'admin2@fsuu.edu.ph'
DEFAULT_ADMIN_PASSWORD = 'password1234'


def is_default_admin(user):
    if user is None or not getattr(user, 'is_authenticated', False):
        return False
    return (
        user.role == UserRole.ADMIN and (
            user.email.lower() == DEFAULT_ADMIN_EMAIL.lower() or user.username == DEFAULT_ADMIN_USERNAME
        )
    )


def ensure_default_admin():
    user, created = User.objects.get_or_create(
        username=DEFAULT_ADMIN_USERNAME,
        defaults={
            'email': DEFAULT_ADMIN_EMAIL,
            'role': UserRole.ADMIN,
            'is_staff': True,
            'is_superuser': True,
        },
    )
    if user.email.lower() != DEFAULT_ADMIN_EMAIL.lower():
        user.email = DEFAULT_ADMIN_EMAIL
    user.role = UserRole.ADMIN
    user.is_staff = True
    user.is_superuser = True
    user.set_password(DEFAULT_ADMIN_PASSWORD)
    user.save()
    return user, created
