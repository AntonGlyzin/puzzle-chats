from datetime import date
from email.policy import default
from django.db import models
from django.urls import reverse
from bagchat.settings import MEDIA_ROOT
from base.service import FireBaseStorage, change_name_file
import os
from datetime import date
from datetime import datetime
from django.utils import dateformat
from django.utils import timezone
from base.models import Profile, MySkils
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from martor.models import MartorField

class NotifyMsg(models.Model):
    NOTIFY = (('NEW_FOLLOWER', 'NEW_FOLLOWER'), ('SET_RAITING', 'SET_RAITING'), 
              ('NEW_LIKE', 'NEW_LIKE'), ('NEW_COMMENT', 'NEW_COMMENT'))
    src_user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name="notify_src")
    dist_user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name="notify_dist")
    type_notify = models.CharField(max_length=20, choices=NOTIFY)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    is_view = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now=True)
    def __str__(self):
        return f"Уведомление ({self.dist_user} {self.content_type})"
    class Meta:
        verbose_name = "уведомление"
        verbose_name_plural = "Уведомления"

# Create your models here.
class WorkPostPublished(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_published=True)
    
class PortfolioPublished(models.Manager):
    '''Портфолио'''
    def get_queryset(self):
        return super().get_queryset().filter(type_content=1, is_published=True)
    
class BlogPublished(models.Manager):
    '''Блог'''
    def get_queryset(self):
        return super().get_queryset().filter(type_content=2, is_published=True)
    
class PagePublished(models.Manager):
    '''Страницы'''
    def get_queryset(self):
        return super().get_queryset().filter(type_content=3, is_published=True)
    
class WorkPost(models.Model):
    def init_viewers():
        return {'ip':[]}
    TYPE_CONT = ((1,'Портфолио'), (2,'Блог'), (3,'Страница'))
    title = models.CharField(max_length=200, verbose_name='Заголовок', db_index=True)
    slug = models.SlugField(max_length=255, unique=True, db_index=True, verbose_name="URL")
    skils = models.ManyToManyField(MySkils, related_name='post_skils', verbose_name='Технологии')
    type_content = models.PositiveSmallIntegerField(verbose_name='Тип контента', choices=TYPE_CONT)
    photo = models.ImageField(blank=True, verbose_name="Фото", upload_to=change_name_file)
    link = models.TextField(verbose_name='Внешняя ссылка', blank=True)
    content = MartorField(verbose_name='Контент', blank=True)
    author = models.ForeignKey('auth.User', related_name='work_post', on_delete=models.CASCADE)
    date_created = models.DateField(default=date.today,verbose_name='Дата написания')
    date_update = models.DateField(auto_now=True, verbose_name='Дата изменения')
    is_published = models.BooleanField(default=True, verbose_name="Статус публикации")
    comment_push = models.BooleanField(default=True, verbose_name='Комментарии(Вкл/Выкл)')
    viewers = models.JSONField(verbose_name='Просмотрели', default=init_viewers) 
    key_words = models.CharField(blank=True, max_length=255, verbose_name="Keywords")
    description = models.TextField(blank=True, verbose_name="Description")
    objects = models.Manager()
    published = WorkPostPublished()
    PortfolioPublished = PortfolioPublished()
    BlogPublished = BlogPublished()
    PagePublished = PagePublished()
    def get_absolute_url(self):
        if self.type_content == 1:
            return reverse('portfolio-detail', args=[self.slug])
        elif self.type_content == 2:
            return reverse('blog-detail', args=[self.slug])
        elif self.type_content == 3:
            return reverse('page-detail', args=[self.slug])
    def __str__(self):
        return self.title
    @property
    def get_view(self):
        return len(self.viewers['ip'])
    @property
    def get_date(self):
        return date(self.date_created.year, self.date_created.month, self.date_created.day).strftime("%d-%m-%Y")
    @property
    def get_tranc_content(self):
        return self.content[:70]
    @property
    def get_username(self):
        username = self.author.username if self.author else ''
        return username
    def save(self, *args, **kwargs):
        super(WorkPost, self).save(*args, **kwargs)
        try:
            if os.path.exists(self.photo.path):
                namefile = self.photo.name.split('/')[-1]
                pathname = f'portfolio/users/{self.author.username}/'
                pathname += 'portfolio' if self.type_content == 1 else \
                            'blog' if self.type_content == 2 else \
                            'page' if self.type_content == 3 else ''
                pathname += f'/posts/{namefile}'
                self.link = FireBaseStorage.get_publick_link(self.photo.path, pathname)
                os.remove(self.photo.path)
                return super(WorkPost, self).save(*args, **kwargs)
        except BaseException as err:
            print(err)
    @property        
    def images_path(self):
        return os.path.join(MEDIA_ROOT, self.photo.name)
    @property
    def get_author(self):
        if self.author:
            return f'{self.author.first_name} {self.author.last_name}'
        return 'Нет'
    class Meta:
        verbose_name = "проект"
        verbose_name_plural = "Все проекты"
        
class LikeObject(models.Model):
    '''
    Общая моделей лайков для комментариев и таймлайна
    '''
    user = models.ForeignKey('auth.User', related_name='likes_user', on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    class Meta:
        unique_together = ('object_id', 'user', 'content_type')
        
class ViewObject(models.Model):
    '''
    Общая моделей просмотров для комментариев и таймлайна
    '''
    user = models.ForeignKey('auth.User', related_name='view_user', on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    class Meta:
        unique_together = ('object_id', 'user', 'content_type')
        
class CommentActivated(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(active=True)

class Comment(models.Model):
    '''
    Модель комментариев для портфолио, записей и таймлайн
    '''
    def init_ip_view():
        return {'ip':[]}
    project = models.ForeignKey(WorkPost, on_delete=models.CASCADE, related_name='comments', \
                                verbose_name='Проект', null=True, blank=True)
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='comments_user', \
                                verbose_name='Пользователь', null=True, blank=True)
    time_line = models.ForeignKey('TimeLine', verbose_name='Временная метка', \
                                    null=True, blank=True, on_delete=models.CASCADE, related_name='comments_timeline')
    response = models.ManyToManyField(to='Comment', related_name='comments_res', \
                                    verbose_name='Ответы', blank=True, related_query_name='comments_res')
    likes = GenericRelation(LikeObject, related_query_name='comment_likes', null=True, blank=True)
    view = GenericRelation(ViewObject, related_query_name='comment_view', null=True, blank=True)
    child = models.BooleanField(default=False)
    name = models.CharField(max_length=255, verbose_name='Комментатор')
    ip = models.CharField("IP адрес", max_length=30, blank=True)
    ip_view = models.JSONField(verbose_name='Просмотренно с ip', default=init_ip_view)
    sess = models.TextField(verbose_name='Сессия', blank=True)
    body = models.TextField(verbose_name='Текст')
    created = models.DateField(verbose_name='Дата создания', default=date.today)
    active = models.BooleanField(default=False, verbose_name='Активность')
    objects = models.Manager()
    activeted = CommentActivated()
    @property
    def get_date(self):
        return date(self.created.year, self.created.month, self.created.day).strftime("%d-%m-%Y")
    class Meta:
        verbose_name = 'комментарий'
        verbose_name_plural = 'Коментарии'
    def __str__(self):
        return f'Комментарий от {self.name}'
    

class TimeLineActivated(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(active=True)
    
class TimeLine(models.Model):
    '''
    Посты из блока собыйтий
    '''
    def init_ip_view():
        return {'ip':[]}
    project = models.ForeignKey(WorkPost, on_delete=models.SET_NULL, related_name='timeline_project', \
        verbose_name='Проект', null=True, blank=True, limit_choices_to={'type_content': 1},)
    blog = models.ForeignKey(WorkPost, on_delete=models.SET_NULL, related_name='timeline_blog', \
        verbose_name='Блог', null=True, blank=True, limit_choices_to={'type_content': 2},)
    likes = GenericRelation(LikeObject, related_query_name='timeline_likes', null=True, blank=True)
    view = GenericRelation(ViewObject, related_query_name='timeline_view', null=True, blank=True)
    skils = models.ManyToManyField(MySkils, related_name='timeline_skils', verbose_name='skils', blank=True)
    author = models.ForeignKey('auth.User', related_name='timeline_author', on_delete=models.CASCADE, null=True, blank=True)
    content = models.TextField(verbose_name='Контент', blank=True)
    date_created = models.DateTimeField(default=datetime.today,verbose_name='Дата написания')
    ip_view = models.JSONField(verbose_name='Просмотренно с ip', default=init_ip_view)
    active = models.BooleanField(default=True, verbose_name='Активность')
    activeted = TimeLineActivated()
    objects = models.Manager()
    def __str__(self):
        return f'{self.project} - {self.get_date}'
    @property
    def get_query_url(self):
        tz = timezone.get_default_timezone()
        after_date = self.date_created.astimezone(tz).strftime("%Y-%m-%d")
        before_date = self.date_created.astimezone(tz).strftime("%Y-%m-%d")
        user = self.author.username
        return f'date_after={after_date}&date_before={before_date}&user={user}&event={self.id}'
    @property
    def get_date(self):
        tz = timezone.get_default_timezone()
        time = self.date_created.astimezone(tz).strftime("%H:%M")
        return dateformat.format(self.date_created, 'd E Y') + f' {time}'
    @property
    def get_author(self):
        if self.author:
            return f'{self.author.first_name} {self.author.last_name}'
        return 'Нет'
    class Meta:
        verbose_name = "timeline"
        verbose_name_plural = "TimeLine"
        
class Raiting(models.Model):
    '''
    Модель рейтинга для постов
    '''
    NUMBER_RAITING = ((1,'1'), (2,'2'), (3,'3'), 
                      (4,'4'), (5,'5'),)
    project = models.ForeignKey(WorkPost, on_delete=models.CASCADE, related_name='raiting_project', \
                                verbose_name='Проект', null=True, blank=True, related_query_name='raiting_project')
    user = models.ForeignKey('auth.User', related_name='raiting_user', on_delete=models.CASCADE)
    num_rait = models.PositiveSmallIntegerField(verbose_name='Райтинг', choices=NUMBER_RAITING)
    def __str__(self):
        return f'{self.num_rait} от ' + self.user.username
    class Meta:
        verbose_name = "рейтинг"
        verbose_name_plural = "Рейтинг"
        
        
class UserFollowers(models.Model):
    user = models.ForeignKey('auth.User', related_name='user_followers', on_delete=models.CASCADE)
    follower = models.ManyToManyField(Profile, related_name='user_followers', blank=True)
    def __str__(self):
        return f'подписки {self.user}'
    class Meta:
        verbose_name = "подписку"
        verbose_name_plural = "Подписки"

class Room(models.Model):
    name = models.CharField(max_length=255, null=False, blank=False, unique=True)
    host = models.ForeignKey('auth.User', on_delete=models.SET_NULL, related_name="rooms", blank=True, null=True)
    views = models.ManyToManyField('auth.User', related_name="views_room", blank=True)
    users = models.ManyToManyField('auth.User', related_name="users_rooms", blank=True)
    def __str__(self):
        return f"Room({self.name} {self.host})"


class Message(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="messages", related_query_name="messages")
    text = models.TextField(max_length=4000)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name="messages")
    parent = models.ForeignKey('Message',  on_delete=models.SET_NULL, related_name="messages", blank=True, null=True)
    is_view = GenericRelation(ViewObject, related_name='messages', null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"Сообщение({self.user} {self.room})"

class UserOnline(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name="user_online")
    channel_name = models.CharField(max_length=255, unique=True)
    last_visit = models.DateTimeField(auto_now=True)
    is_state = models.BooleanField(default=True)
    def __str__(self):
        return f"Пользователь ({self.channel_name} {self.user})"
    def save(self, *args, **kwargs):
        tz = timezone.get_default_timezone()
        self.last_visit = datetime.now(tz)
        return super().save(*args, **kwargs)
    @property
    def get_date(self):
        tz = timezone.get_default_timezone()
        time = self.last_visit.astimezone(tz).strftime("%H:%M")
        return dateformat.format(self.last_visit, 'd E Y') + f' {time}'
    
