# Generated by Django 2.1.7 on 2019-03-26 20:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('library', '0006_peer_review_update'),
    ]

    operations = [
        migrations.AlterField(
            model_name='codebaserelease',
            name='os',
            field=models.CharField(blank=True, choices=[('other', 'Other'), ('linux', 'Unix/Linux'), ('macos', 'Mac OS'), ('windows', 'Windows'), ('platform_independent', 'Operating System Independent')], max_length=32),
        ),
    ]
