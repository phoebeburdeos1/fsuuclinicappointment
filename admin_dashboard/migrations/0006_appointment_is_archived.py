from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admin_dashboard', '0005_appointment_patient_archived'),
    ]

    operations = [
        migrations.AddField(
            model_name='appointment',
            name='is_archived',
            field=models.BooleanField(default=False),
        ),
    ]