# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2017-12-22 13:13
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0005_billinginvoice'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='billing',
            name='trial_started',
        ),
    ]
