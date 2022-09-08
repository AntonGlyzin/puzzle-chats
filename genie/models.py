from django.db import models
from telebot import TeleBot
from bagchat.settings import ME_CHAT_ID, TOKEN_BOT_GLYZIN
import os
from base.service import FireBaseStorage

class UserActive(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(active=True)

class UserTemplate(models.Model):
    DAYS = ((i,i) for i in range(1,32))
    MONTHS = ((i,i) for i in range(1,13))
    GENDER = ((1,'М'), (2,'Ж'))
    id_user = models.CharField(unique=True, verbose_name='Чат-ID', max_length=50)
    username = models.CharField(verbose_name='Пользователь', max_length=50, blank=True)
    sex = models.PositiveSmallIntegerField(verbose_name='Пол', choices=GENDER, null=True, blank=True)
    linkname = models.CharField(verbose_name='Ссылка на пользователя', max_length=50, blank=True)
    day_user = models.PositiveSmallIntegerField(verbose_name='День', choices=DAYS, null=True, blank=True)
    month_user = models.PositiveSmallIntegerField(verbose_name='Месяц', choices=MONTHS, null=True, blank=True)
    content = models.TextField(verbose_name='Шаблон ответа', blank=True)
    time_create = models.DateField(auto_now_add=True, verbose_name="Время регистрации")
    active = models.BooleanField(default=True, verbose_name='Доступность')
    objects = models.Manager()
    activated = UserActive()
    def __str__(self):
        return f'{self.username}'
    class Meta:
        verbose_name = "пользователя"
        verbose_name_plural = "Пользователи"
        
        
class Holidays(models.Model):
    DAYS = ((i,i) for i in range(0,32))
    MONTHS = ((i,i) for i in range(0,13))
    TYPS_HOLYD = ((1,'М'), (2,'Ж'), (3,'Общий'))
    day = models.PositiveSmallIntegerField(verbose_name='День', choices=DAYS)
    month = models.PositiveSmallIntegerField(verbose_name='Месяц', choices=MONTHS)
    description = models.CharField(verbose_name='Праздник', max_length=100)
    type_holiday = models.PositiveSmallIntegerField(verbose_name='Чей праздник', choices=TYPS_HOLYD, blank=True)
    def __str__(self):
        return f'{self.description}'
    class Meta:
        verbose_name = "праздник"
        verbose_name_plural = "Праздники"
        unique_together = (('day', 'month'),)
        
        
class PicsHolidays(models.Model):
    FOR_CONT = ((1,'М'), (2,'Ж'), (3,'Общий'))
    TYPS_CONT = ((1,'Фото'), (2,'Стикер'))
    link = models.TextField(verbose_name='Внешняя ссылка', blank=True)
    view = models.ImageField(blank=True, verbose_name="Фото к празднику")
    photo = models.CharField(blank=True, verbose_name="ИД фото", max_length=200)
    for_cont = models.PositiveSmallIntegerField(verbose_name='Для кого контент', choices=FOR_CONT, null=True, blank=True)
    type_cont = models.PositiveSmallIntegerField(verbose_name='Тип контента', choices=TYPS_CONT, null=True, blank=True)
    holidays = models.ForeignKey(Holidays, on_delete=models.CASCADE, related_name='pics_holidays', verbose_name='Праздник',
                             null=True, blank=True)
    def __str__(self):
        return f'{self.holidays}'
    def save(self, *args, **kwargs):
        super(PicsHolidays, self).save(*args, **kwargs)
        try:
            if os.path.exists(self.view.path):
                namefile = self.view.name.split('/')[-1]
                dist_pathname = f'holidays/photo/{namefile}'
                self.link = FireBaseStorage.get_publick_link(self.view.path, dist_pathname)
                bot = TeleBot(TOKEN_BOT_GLYZIN, threaded=False)
                res = bot.send_photo(ME_CHAT_ID, open(f'{self.view.path}', 'rb'))
                self.photo = res.photo[-1].file_id
                os.remove(self.view.path)
                return super(PicsHolidays, self).save(*args, **kwargs)
        except BaseException as err:
            print(err)
    class Meta:
        verbose_name = "картинку"
        verbose_name_plural = "Фото к празднику"
        
        
class TextHolidays(models.Model):
    FOR_CONT = ((1,'М'), (2,'Ж'), (3,'Общий'))
    content = models.TextField(verbose_name='Поздравление')
    for_cont = models.PositiveSmallIntegerField(verbose_name='Для кого контент', choices=FOR_CONT, null=True, blank=True)
    holidays = models.ForeignKey(Holidays, on_delete=models.CASCADE, related_name='text_holidays', verbose_name='Праздник',
                             null=True, blank=True)
    def __str__(self):
        return f'{self.holidays}'
    class Meta:
        verbose_name = "поздравление"
        verbose_name_plural = "Поздравления"
        
        
class audioHolidays(models.Model):
    FOR_CONT = ((1,'М'), (2,'Ж'), (3,'Общий'))
    file_audio = models.FileField(verbose_name='')
    file_id = models.CharField(blank=True, verbose_name="ИД audio", max_length=200)
    link = models.TextField(verbose_name='Внешняя ссылка', blank=True)
    for_cont = models.PositiveSmallIntegerField(verbose_name='Для кого контент', choices=FOR_CONT, null=True, blank=True)
    holidays = models.ForeignKey(Holidays, on_delete=models.CASCADE, related_name='audio_holidays', verbose_name='Праздник',
                             null=True, blank=True)
    def __str__(self):
        return f'{self.holidays}'
    def save(self, *args, **kwargs):
        super(audioHolidays, self).save(*args, **kwargs)
        try:
            if os.path.exists(self.file_audio.path):
                namefile = self.file_audio.name.split('/')[-1]
                dist_pathname = f'holidays/audio/{namefile}'
                self.link = FireBaseStorage.get_publick_link(self.file_audio.path, dist_pathname)
                bot = TeleBot(TOKEN_BOT_GLYZIN, threaded=False)
                res = bot.send_audio(ME_CHAT_ID, open(f'{self.file_audio.path}', 'rb'))
                self.file_id = res.audio.file_id
                os.remove(self.file_audio.path)
                return super(audioHolidays, self).save(*args, **kwargs)
        except BaseException as err:
            print(err)
    class Meta:
        verbose_name = "музыку"
        verbose_name_plural = "Музыка"
        
    