# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2017-11-21 15:49
from __future__ import unicode_literals

from django.db import migrations
import django.db.models.manager


class Migration(migrations.Migration):

    dependencies = [
        ('cases', '0020_auto_20170419_0926'),
    ]

    operations = [
        migrations.AlterModelManagers(
            name='case',
            managers=[
                ('elastic_objects', django.db.models.manager.Manager()),
                ('objects', django.db.models.manager.Manager()),
            ],
        ),
    ]
