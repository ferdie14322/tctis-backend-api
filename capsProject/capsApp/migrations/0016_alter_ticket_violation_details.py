# Generated by Django 5.1.4 on 2025-01-01 23:57

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('capsApp', '0015_remove_ticket_firstname_remove_ticket_lastname_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ticket',
            name='violation_details',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='capsApp.violation'),
        ),
    ]
