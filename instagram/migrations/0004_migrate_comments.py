from django.db import migrations

def migrate_comment_logs(apps, schema_editor):
    CommentLog = apps.get_model('instagram', 'CommentLog')
    InstagramComment = apps.get_model('instagram', 'InstagramComment')
    
    comments_to_create = []
    for log in CommentLog.objects.select_related('reel__account').all():
        if not InstagramComment.objects.filter(comment_id=log.comment_id).exists():
            comments_to_create.append(
                InstagramComment(
                    account=log.reel.account,
                    comment_id=log.comment_id,
                    media_id=log.reel.reel_id,
                    username=log.commenter_username,
                    text=log.comment_text,
                    timestamp=log.created_at,
                    processed=log.processed
                )
            )
    if comments_to_create:
        InstagramComment.objects.bulk_create(comments_to_create)

class Migration(migrations.Migration):

    dependencies = [
        ('instagram', '0003_instagramcomment'),
    ]

    operations = [
        migrations.RunPython(migrate_comment_logs, reverse_code=migrations.RunPython.noop),
    ]
