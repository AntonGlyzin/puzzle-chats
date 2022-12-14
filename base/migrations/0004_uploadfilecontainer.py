# Generated by Django 4.0.6 on 2022-07-21 04:44

from django.db import migrations, models
import pathlib


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0003_alter_imageslink_photo_alter_profile_photo'),
    ]

    operations = [
        migrations.CreateModel(
            name='UploadFileContainer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(blank=True, upload_to=pathlib.PurePosixPath('/app'), verbose_name='Файл')),
            ],
            options={
                'verbose_name': 'Файл в контейнере',
                'verbose_name_plural': 'Файл в контейнер',
            },
        ),
    ]
