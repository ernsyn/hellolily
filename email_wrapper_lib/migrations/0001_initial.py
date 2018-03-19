# -*- coding: utf-8 -*-
# Generated by Django 1.11.10 on 2018-03-16 14:12
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import email_wrapper_lib.models.mixins
import oauth2client.contrib.django_orm


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='EmailAccount',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('username', models.CharField(max_length=255, unique=True, verbose_name='Username')),
                ('user_id', models.CharField(max_length=255, unique=True, verbose_name='User id')),
                ('raw_credentials', oauth2client.contrib.django_orm.CredentialsField(null=True)),
                ('status', models.PositiveSmallIntegerField(choices=[(0, 'new'), (1, 'idle'), (2, 'syncing'), (3, 'error'), (4, 'resync')], db_index=True, default=0, verbose_name='Status')),
                ('provider', models.PositiveSmallIntegerField(choices=[(0, b'Google'), (1, b'Microsoft')], db_index=True, verbose_name='Provider id')),
                ('subscription_id', models.CharField(max_length=255, null=True, verbose_name='Subscription id')),
                ('messages_count', models.PositiveIntegerField(verbose_name='Total number of messages')),
                ('threads_count', models.PositiveIntegerField(verbose_name='Total number of threads')),
            ],
            bases=(email_wrapper_lib.models.mixins.SoftDeleteMixin, email_wrapper_lib.models.mixins.TimeStampMixin, models.Model),
        ),
        migrations.CreateModel(
            name='EmailFolder',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('parent_id', models.CharField(max_length=255, null=True, verbose_name='Parent')),
                ('remote_id', models.CharField(db_index=True, max_length=255, verbose_name='Remote id')),
                ('remote_value', models.CharField(max_length=255, verbose_name='Remote value')),
                ('name', models.CharField(max_length=255, verbose_name='Name')),
                ('folder_type', models.PositiveSmallIntegerField(choices=[(0, 'System'), (1, 'User')], verbose_name='Folder type')),
                ('messages_count', models.PositiveIntegerField(verbose_name='Total number of messages')),
                ('messages_unread_count', models.PositiveIntegerField(verbose_name='Unread number of messages')),
                ('threads_count', models.PositiveIntegerField(verbose_name='Total number of threads')),
                ('threads_unread_count', models.PositiveIntegerField(verbose_name='Unread number of threads')),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='folders', to='email_wrapper_lib.EmailAccount', verbose_name='Account')),
            ],
        ),
        migrations.CreateModel(
            name='EmailMessage',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('remote_id', models.CharField(max_length=255, verbose_name='Remote id')),
                ('thread_id', models.CharField(max_length=255, verbose_name='Thread id')),
                ('mime_message_id', models.CharField(max_length=255, verbose_name='MIME message id')),
                ('snippet', models.TextField(verbose_name='Snippet')),
                ('subject', models.TextField(verbose_name='Subject')),
                ('received_date_time', models.DateTimeField(verbose_name='Date')),
                ('is_read', models.BooleanField(verbose_name='Is read')),
                ('is_starred', models.BooleanField(verbose_name='Is starred')),
                ('has_attachments', models.BooleanField(verbose_name='Has attachment')),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='email_wrapper_lib.EmailAccount', verbose_name='Account')),
                ('folders', models.ManyToManyField(related_name='messages', to='email_wrapper_lib.EmailFolder', verbose_name='Folder')),
            ],
        ),
        migrations.CreateModel(
            name='EmailMessageToEmailRecipient',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('recipient_type', models.PositiveSmallIntegerField(choices=[(0, 'To'), (1, 'CC'), (2, 'BCC'), (3, 'From'), (4, 'Sender'), (5, 'Reply to')], verbose_name='Recipient type')),
                ('message', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='email_wrapper_lib.EmailMessage', verbose_name='Message')),
            ],
        ),
        migrations.CreateModel(
            name='EmailRecipient',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='Name')),
                ('email_address', models.EmailField(max_length=254, verbose_name='Email')),
                ('raw_value', models.CharField(db_index=True, max_length=509, unique=True, verbose_name='Raw value')),
            ],
        ),
        migrations.CreateModel(
            name='GoogleSyncInfo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('history_id', models.CharField(max_length=255, null=True, verbose_name='History token')),
                ('account', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='google_sync_info', to='email_wrapper_lib.EmailAccount', verbose_name='Account')),
            ],
        ),
        migrations.CreateModel(
            name='MicrosoftSyncInfo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('history_id', models.CharField(max_length=255, null=True, verbose_name='History token')),
                ('folder', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='microsoft_sync_info', to='email_wrapper_lib.EmailFolder', verbose_name='Folder')),
            ],
        ),
        migrations.AddField(
            model_name='emailmessagetoemailrecipient',
            name='recipient',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='email_wrapper_lib.EmailRecipient', verbose_name='Recipient'),
        ),
        migrations.AddField(
            model_name='emailmessage',
            name='recipients',
            field=models.ManyToManyField(related_name='messages', through='email_wrapper_lib.EmailMessageToEmailRecipient', to='email_wrapper_lib.EmailRecipient', verbose_name='Recipients'),
        ),
        migrations.AlterUniqueTogether(
            name='emailfolder',
            unique_together=set([('account', 'remote_id', 'remote_value')]),
        ),
    ]
