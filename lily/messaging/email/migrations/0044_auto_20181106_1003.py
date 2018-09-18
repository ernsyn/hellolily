# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2018-11-06 10:03
from __future__ import unicode_literals

import django.contrib.postgres.fields
import django.contrib.postgres.fields.jsonb
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import lily.messaging.email.models.models
import re


class Migration(migrations.Migration):

    dependencies = [
        ('tenant', '0008_auto_20180822_1308'),
        ('email', '0043_auto_20180906_1300'),
    ]

    operations = [
        migrations.CreateModel(
            name='EmailDraft',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('to', django.contrib.postgres.fields.ArrayField(base_field=models.EmailField(max_length=254), size=None, verbose_name='to')),
                ('cc', django.contrib.postgres.fields.ArrayField(base_field=models.EmailField(max_length=254), size=None, verbose_name='cc')),
                ('bcc', django.contrib.postgres.fields.ArrayField(base_field=models.EmailField(max_length=254), size=None, verbose_name='bcc')),
                ('headers', django.contrib.postgres.fields.jsonb.JSONField(default=dict, verbose_name='email headers')),
                ('subject', models.CharField(blank=True, max_length=255, verbose_name='subject')),
                ('body', models.TextField(blank=True, verbose_name='html body')),
                ('mapped_attachments', models.IntegerField(verbose_name='number of mapped attachments')),
                ('original_attachment_ids', models.TextField(default=b'', validators=[django.core.validators.RegexValidator(re.compile('^\\d+(?:\\,\\d+)*\\Z'), code='invalid', message='Enter only digits separated by commas.')])),
                ('template_attachment_ids', models.CharField(default=b'', max_length=255, validators=[django.core.validators.RegexValidator(re.compile('^\\d+(?:\\,\\d+)*\\Z'), code='invalid', message='Enter only digits separated by commas.')])),
                ('original_message_id', models.CharField(blank=True, db_index=True, default=b'', max_length=50)),
                ('send_from', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='draft_messages', to='email.EmailAccount', verbose_name='from')),
                ('tenant', models.ForeignKey(blank=True, on_delete=django.db.models.deletion.CASCADE, to='tenant.Tenant')),
            ],
            options={
                'verbose_name': 'email draft message',
                'verbose_name_plural': 'email draft messages',
            },
        ),
        migrations.CreateModel(
            name='EmailDraftAttachment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('inline', models.BooleanField(default=False)),
                ('attachment', models.FileField(max_length=255, upload_to=lily.messaging.email.models.models.get_outbox_attachment_upload_path)),
                ('size', models.PositiveIntegerField(default=0)),
                ('content_type', models.CharField(max_length=255, verbose_name='content type')),
                ('email_draft', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attachments', to='email.EmailDraft')),
                ('tenant', models.ForeignKey(blank=True, on_delete=django.db.models.deletion.CASCADE, to='tenant.Tenant')),
            ],
            options={
                'verbose_name': 'email draft attachment',
                'verbose_name_plural': 'email draft attachments',
            },
        ),
        migrations.AddField(
            model_name='emailmessage',
            name='received_by_bcc',
            field=models.ManyToManyField(related_name='received_messages_as_bcc', to='email.Recipient'),
        ),
    ]
