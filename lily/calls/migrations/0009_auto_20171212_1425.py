# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2017-12-12 14:25
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tenant', '0006_auto_20170825_1253'),
        ('calls', '0008_auto_20171116_0842'),
    ]

    operations = [
        migrations.AlterField(
            model_name='callrecord',
            name='call_id',
            field=models.CharField(max_length=255, verbose_name='Call id'),
        ),
        migrations.AlterUniqueTogether(
            name='callrecord',
            unique_together=set([('tenant', 'call_id')]),
        ),
    ]