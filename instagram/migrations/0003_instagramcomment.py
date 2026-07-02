# Generated manually for InstagramComment

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('instagram', '0002_whatsappaccount'),
    ]

    operations = [
        migrations.CreateModel(
            name='InstagramComment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('comment_id', models.CharField(max_length=255, unique=True)),
                ('media_id', models.CharField(max_length=255)),
                ('username', models.CharField(max_length=255)),
                ('text', models.TextField()),
                ('timestamp', models.DateTimeField()),
                ('processed', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='all_comments', to='instagram.instagramaccount')),
            ],
        ),
    ]
