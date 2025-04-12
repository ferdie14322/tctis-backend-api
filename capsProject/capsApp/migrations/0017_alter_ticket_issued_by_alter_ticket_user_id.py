# Generated by Django 5.1.4 on 2025-01-02 00:06

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('capsApp', '0016_alter_ticket_violation_details'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ticket',
            name='issued_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='tickets_as_issuer', to='capsApp.user'),
        ),
        migrations.AlterField(
            model_name='ticket',
            name='user_id',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='tickets_as_user', to='capsApp.user'),
        ),
    ]
