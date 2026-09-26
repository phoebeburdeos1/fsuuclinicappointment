from django.contrib.auth.hashers import make_password
from django.db import migrations


def create_default_admin(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    User.objects.filter(username='admin2').delete()
    admin = User.objects.create(
        username='admin2',
        email='admin2@fsuu.edu.ph',
        role='ADMIN',
        is_staff=True,
        is_superuser=True,
        first_name='FSUU',
        last_name='Hospital',
        password=make_password('password1234'),
    )
    admin.save(update_fields=['password', 'email', 'role', 'is_staff', 'is_superuser', 'first_name', 'last_name'])


def reverse_default_admin(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    User.objects.filter(username='admin2').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_default_admin, reverse_default_admin),
    ]
