import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inbox', '0001_initial'),
        ('instagram', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='conversation',
            name='conversation_id',
            field=models.CharField(blank=True, max_length=255, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='conversation',
            name='instagram_account',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='conversations', to='instagram.instagramaccount'),
        ),
        migrations.AddField(
            model_name='conversation',
            name='participants',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='conversation',
            name='last_message_timestamp',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='message',
            name='processed',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='message',
            name='raw_payload',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='message',
            name='sender_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='message',
            name='sender_username',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='message',
            name='message_type',
            field=models.CharField(default='text', max_length=50),
        ),
        migrations.AddField(
            model_name='message',
            name='timestamp',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
