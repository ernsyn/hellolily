# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2018-01-22 12:57
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0006_remove_billing_trial_started'),
    ]

    operations = [
        migrations.AddField(
            model_name='billing',
            name='trial_end',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
