import datetime
from django.db import models
import os
from bagchat.settings import MEDIA_ROOT, BASE_DIR
from .service import FireBaseStorage, change_name_file
from django.conf import settings
from easy_thumbnails.files import get_thumbnailer
from django.contrib.contenttypes.fields import GenericRelation
from django.utils import dateformat
from django.utils import timezone
import shutil

class ImagesLink(models.Model):
    name = models.CharField(max_length=200, verbose_name='Название фото', blank=True, help_text='По желанию (нужно для переминование картинки)')
    photo = models.ImageField(blank=True, verbose_name="Фото", max_length=255, upload_to=change_name_file)
    link = models.TextField(verbose_name='Внешняя ссылка', blank=True)
    def __str__(self):
        return f'{self.photo.name}'
    def save(self, *args, **kwargs):
        super(ImagesLink, self).save(*args, **kwargs)
        try:
            if os.path.exists(self.photo.path):
                namefile = self.photo.name.split('/')[-1]
                extend = namefile.split('.')[-1]
                pathname = 'portfolio/photo/'
                pathname += f'{self.name}.{extend}'.replace(' ','') if self.name else f'{namefile}'
                self.name = ''
                self.link = FireBaseStorage.get_publick_link(self.photo.path, pathname)
                options = {'size': (100, 100), 'crop': True}
                thumb_url = get_thumbnailer(self.photo).get_thumbnail(options).url
                os.remove(self.photo.path)
                namefile = thumb_url.split('/')[-1]
                pathname = 'portfolio/photo/' + namefile
                self.photo = FireBaseStorage.get_publick_link(os.path.join(MEDIA_ROOT, namefile), pathname)
                os.remove(os.path.join(MEDIA_ROOT, namefile))
                return super(ImagesLink, self).save(*args, **kwargs)
        except BaseException as err:
            print(err)
    class Meta:
        verbose_name = "картинку"
        verbose_name_plural = "Картинки"

class PortfolioUser(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(type_app = 1, user__is_active=True)
    
class ActiveUser(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(user__is_active=True)
    
class MySkils(models.Model):
    name = models.CharField(verbose_name='Способность', max_length=50, unique=True)
    slug = models.CharField(verbose_name='Slug', max_length=50, unique=True, db_index=True)
    def __str__(self):
        return self.name
    class Meta:
        verbose_name = "способность"
        verbose_name_plural = "Skils"

class Profile(models.Model):
    def init_my_ip():
        return {'ip':[]}
    def init_resume():
        resum = {
            'birthday': '',
            'mycity': '',
            'needWork': '',
            'myphone': '',
            'userWorks': [
                {
                    'pred': '',
                    'doljn': '',
                    'years': '',
                    'mywork': ''
                }
            ],
            'userStudy': [
                {
                    'pred': '',
                    'years': '',
                    'form': '',
                    'fac': '',
                    'spec': ''
                }
            ],
            'plusStudy': [
                {
                    'pred': '',
                    'years': '',
                    'name': ''
                }
            ],
            'iDostig': '',
            'myHobby': '',
            'myLang': '',
            'aboutme': ''
        }
        return resum
    TYPE_USER= ((1,'Портфолио'), )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, \
                            verbose_name='Пользователь', related_name='profile_user')
    date_of_birth = models.DateField(blank=True, null=True, verbose_name='День рождение')
    photo = models.ImageField(upload_to=change_name_file, blank=True, verbose_name='Картинка', max_length=255)
    myskils = models.ManyToManyField(MySkils, related_name='profile_myskils', verbose_name='Skils', blank=True)
    links = models.TextField(verbose_name='Внешние источники в JSON', blank=True)
    photo_user = models.TextField(verbose_name='Ссылка на фото', blank=True, null=True)
    resume = models.JSONField(verbose_name='Для резюме', default=init_resume)
    my_ip = models.JSONField(verbose_name='Мои ip', default=init_my_ip)
    type_app = models.PositiveSmallIntegerField(verbose_name='Приложение', choices=TYPE_USER, blank=True, null=True)
    telegram = models.CharField(verbose_name='Telegram пользователя', max_length=50, blank=True)
    keyword = models.CharField(verbose_name='Слово для активации', max_length=10, blank=True)
    last_token = models.TextField(max_length=500, blank=True, verbose_name='Токен чата')
    objects = models.Manager()
    PortfolioActive = PortfolioUser()
    user_active = ActiveUser()
    def __str__(self):
        fullname = self.user.get_full_name()
        return f'{self.user.username} - {fullname}' if fullname else f'{self.user.username}'
    def save(self, *args, **kwargs):
        super(Profile, self).save(*args, **kwargs)
        try:
            if os.path.exists(self.photo.path):
                namefile = self.photo.name.split('/')[-1]
                pathname = f'portfolio/users/{self.user.username}/avatar/{namefile}'
                self.photo_user = FireBaseStorage.get_publick_link(self.photo.path, pathname)
                options = {'size': (100, 100), 'crop': True}
                thumb_url = get_thumbnailer(self.photo).get_thumbnail(options).url
                os.remove(self.photo.path)
                namefile = thumb_url.split('/')[-1]
                pathname = f'portfolio/users/{self.user.username}/avatar/{namefile}'
                self.photo = FireBaseStorage.get_publick_link(os.path.join(MEDIA_ROOT, namefile), pathname)
                os.remove(os.path.join(MEDIA_ROOT, namefile))
                return super(Profile, self).save(*args, **kwargs)
        except BaseException as err:
            print(err)
    class Meta:
        unique_together = ('user', 'type_app',)
        verbose_name = "профиль"
        verbose_name_plural = "Профиль"
        
    

    
