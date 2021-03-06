# -*- coding: utf-8 -*-
# Generated by Django 1.11.11 on 2018-06-26 14:42
from __future__ import unicode_literals

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0026_set_registration_finished_to_true'),
    ]

    operations = [
        migrations.CreateModel(
            name='BrowserSettings',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data', django.contrib.postgres.fields.jsonb.JSONField(default={})),
            ],
        ),
        migrations.AddField(
            model_name='lilyuser',
            name='browser_settings',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='users.BrowserSettings'),
        ),
    ]
