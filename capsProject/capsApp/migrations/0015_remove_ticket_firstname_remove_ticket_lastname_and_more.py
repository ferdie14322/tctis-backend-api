# Generated by Django 5.1.4 on 2025-01-01 23:32

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('capsApp', '0014_alter_ticket_issued_by'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='ticket',
            name='firstname',
        ),
        migrations.RemoveField(
            model_name='ticket',
            name='lastname',
        ),
        migrations.AddField(
            model_name='ticket',
            name='user_id',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='capsApp.user'),
        ),
    ]
