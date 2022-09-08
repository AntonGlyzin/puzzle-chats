from django.http import HttpResponse
import json
import os
from django.views.decorators.csrf import csrf_exempt
from telebot import TeleBot
from google.cloud import dialogflow
from google.protobuf.json_format import MessageToDict
import random
from django.views.decorators.http import require_POST
from genie.models import UserTemplate, Holidays
from django.utils import timezone
import re
from telebot import types
from django.views.decorators.http import require_http_methods
from bagchat.settings import ME_CHAT_ID, TOKEN_BOT_GLYZIN, BASE_DIR
import string
from base.models import Profile
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from datetime import datetime
from django.utils import dateformat

DIALOGFLOW_PROJECT_ID = 'genie-hkdf'
DIALOGFLOW_LANGUAGE_CODE = 'ru'
SESSION_ID = 'me'
ME_ID = ME_CHAT_ID
bot = TeleBot(TOKEN_BOT_GLYZIN, threaded=False)

MY_SITE = 'https://portfolio-puzzle.web.app/card/user/toshaglyzin'
mess_start = 'Давай дружить?\nВот, что я умею делать:\n\
1. Могу пообщаться и поддержать в трудную минуту.\n\
2. Могу принимать сообщения с сайта и\
 отправлять в телеграмм.\n\
3. Также поздравляю каждые праздники и дни рождения.'

@csrf_exempt
@require_POST
def entryGenie(request):
    '''
    Точка входа для телеграмма.
    '''
    print(request)
    user = json.loads(request.body)
    update = types.Update.de_json(json.dumps(user))
    bot.process_new_updates([update])
    return HttpResponse(status=200)


@bot.message_handler(content_types=["photo"])
def forphoto(message):
    if ME_CHAT_ID == message.from_user.id:
        js = message.json['photo'][-1]['file_id']
        bot.send_message(message.from_user.id, f'{js}')


@bot.message_handler(content_types=["sticker"])
def for_sticker(message):
    if ME_CHAT_ID == message.from_user.id:
        bot.send_message(message.from_user.id, f'{message.sticker.file_id}')

@bot.message_handler(content_types=["animation"])
def for_animation(message):
    if ME_CHAT_ID == message.from_user.id:
        bot.send_message(message.from_user.id, f'{message.animation.file_id}')

@bot.message_handler(content_types=["audio"])
def for_audio(message):
    if ME_CHAT_ID == message.from_user.id:
        bot.send_message(message.from_user.id, f'{message.audio.file_id}')


# @bot.message_handler(commands=['sendVoice'])
# def send_Voice(message):
#     '''
#     Обработка команды старт
#     '''

#     if ME_CHAT_ID == message.chat.id:
#         # res = bot.send_message(message.chat.id, 'ID')
#         bot.send_voice(message.from_user.id, 'CQACAgIAAxkBAAIJHmJviw1l0Sg5QwXc12FXPLdjrmatAAK-GQACUJl4S6h7wDBxRTaPJAQ')
#         # bot.register_next_step_handler(res, func_res)

# def func_res(message):
#     txt = message.text.stri()
#     bot.send_voice(message.from_user.id, txt)

    
def checkHolidays():
    '''
    Проверка праздников и дней рождений, а также поздравление.
    '''
    now_day = timezone.now().day
    now_month = timezone.now().month
    holiday = Holidays.objects.filter(day=now_day, month=now_month)

    def send_mess(id, text_day, rand_text_day, photo_day, rand_photo_day, \
                        dontneed, rand_audio_day, audio_day, name = ''):
        for_cont = rand_photo_day.get('pics_holidays__for_cont', '')
        len_photo = len(photo_day)*5
        while for_cont == dontneed:
            if len_photo <= 0:
                rand_photo_day = {}
                break
            rand_photo_day = random.choice(photo_day)
            for_cont = rand_photo_day.get('pics_holidays__for_cont', '')
            len_photo -= 1

        for_cont = rand_text_day.get('text_holidays__for_cont', '')
        len_text = len(text_day)*5
        while for_cont == dontneed:
            if len_text <= 0:
                rand_text_day = {}
                break
            rand_text_day = random.choice(text_day)
            for_cont = rand_text_day.get('text_holidays__for_cont', '')
            len_text -= 1

        for_cont = rand_audio_day.get('audio_holidays__for_cont', '')
        len_audio = len(audio_day)*5
        while for_cont == dontneed:
            if len_audio <= 0:
                rand_audio_day = {}
                break
            rand_audio_day = random.choice(audio_day)
            for_cont = rand_audio_day.get('audio_holidays__for_cont', '')
            len_audio -= 1

        txt = rand_text_day.get('text_holidays__content', '')
        txt = txt.replace('[name]', name) if txt else None
        img = rand_photo_day.get('pics_holidays__photo', '')
        img = img.strip() if img else None
        audio = rand_audio_day.get('audio_holidays__file_id', '')
        type = rand_photo_day.get('pics_holidays__type_cont', '')
        bot.send_message(id, txt) if txt else None
        if type == 2:
            bot.send_sticker(id, img) if img else None
        else:
            bot.send_photo(id, img) if img else None
        bot.send_audio(id, audio) if audio else None
        
    if holiday:
        photo_day = holiday.values('type_holiday','pics_holidays__photo','pics_holidays__type_cont','pics_holidays__for_cont')
        text_day = holiday.values('type_holiday','text_holidays__content', 'text_holidays__for_cont')
        audio_day = holiday.values('type_holiday','audio_holidays__file_id', 'audio_holidays__for_cont')
        users = UserTemplate.activated.all().values('id_user', 'username', 'sex')
        for user in users:
            try:
                rand_photo_day= random.choice(photo_day)
                rand_text_day = random.choice(text_day)
                rand_audio_day = random.choice(audio_day)
                img = rand_photo_day.get('pics_holidays__photo', '')
                img = img.strip() if img else None
                text = rand_text_day.get('text_holidays__content', '')
                audio = rand_audio_day.get('audio_holidays__file_id', '')
                if rand_photo_day['type_holiday'] == 1:
                    if user['sex'] == 1:
                        bot.send_message(user['id_user'], text) if text else None
                        bot.send_photo(user['id_user'], img) if img else None
                        bot.send_audio(user['id_user'], audio) if audio else None
                elif rand_photo_day['type_holiday'] == 2:
                    if user['sex'] == 2:
                        bot.send_message(user['id_user'], text) if text else None
                        bot.send_photo(user['id_user'], img) if img else None
                        bot.send_audio(user['id_user'], audio) if audio else None
                elif rand_photo_day['type_holiday'] == 3:
                    if user['sex'] == 1:
                        send_mess(user['id_user'], text_day, rand_text_day, \
                            photo_day, rand_photo_day, 2, rand_audio_day, audio_day, user['username'].split(' ')[0])
                    else:
                        send_mess(user['id_user'], text_day, rand_text_day, \
                            photo_day, rand_photo_day, 1, rand_audio_day, audio_day, user['username'].split(' ')[0])
            except BaseException as err:
                print(err)
    users_birth = UserTemplate.activated.filter(day_user=now_day, month_user=now_month).values('id_user', 'username', 'sex')
    if users_birth:
        birthday = Holidays.objects.filter(day=0, month=0)
        if birthday:
            photo_birthday = birthday.values('pics_holidays__photo','pics_holidays__type_cont','pics_holidays__for_cont')
            text_birthday = birthday.values('text_holidays__content', 'text_holidays__for_cont')
            audio_birthday = birthday.values('audio_holidays__file_id', 'audio_holidays__for_cont')
            for user_birth in users_birth:
                try:
                    rand_photo_day = random.choice(photo_birthday)
                    rand_text_day = random.choice(text_birthday)
                    rand_audio_day = random.choice(audio_birthday)
                    if user_birth['sex'] == 1:
                        send_mess(user_birth['id_user'], text_birthday, rand_text_day, \
                            photo_birthday, rand_photo_day, 2, rand_audio_day, audio_birthday, user_birth['username'].split(' ')[0])
                    else:
                        send_mess(user_birth['id_user'], text_birthday, rand_text_day, \
                            photo_birthday, rand_photo_day, 1, rand_audio_day, audio_birthday, user_birth['username'].split(' ')[0])
                except BaseException as err:
                    print(err)
    # return HttpResponse(status=200)


@bot.message_handler(commands=['randletters'])
def rand_letters(message):
    '''
    Обработка команды случайных символов
    '''
    add_count = bot.send_message(message.from_user.id, 'Сколько должно быть символов в строке?')
    def func_add_count_letters(message):
        count = message.text.strip()
        if count.isdigit():
            ran = ''.join(random.choices(string.ascii_letters + string.digits, k = int(count)))
            bot.send_message(message.from_user.id, f'{ran}')
    bot.register_next_step_handler(add_count, func_add_count_letters)


@bot.message_handler(commands=['myportfolio'])
def my_portfolio(message):
    profile = Profile.objects.filter(telegram=message.from_user.id)
    if not profile:
        url = types.InlineKeyboardButton(text="Регистрация", url='https://portfolio-puzzle.web.app/aboutme')
        prof = types.InlineKeyboardButton(text="Активировать портфолио", callback_data="active_portfolio")
        bot.send_message(message.from_user.id, 'Ваш профиль не активен или еще не создан.', \
             reply_markup=types.InlineKeyboardMarkup().add(url).add(prof))
    else:
        if profile[0].user.is_active == False:
            bot.send_message(message.from_user.id, 'Профиль заблокирован.')
        else:
            set_pass_portfolio = types.InlineKeyboardButton(text="Изменить пароль?", callback_data="set_pass_portfolio")
            bot.send_message(message.from_user.id, 'Привет. Что желаете?', \
                reply_markup=types.InlineKeyboardMarkup().add(set_pass_portfolio))


@bot.message_handler(commands=['author'])
def send_author(message):
    '''
    Обработка команды автор
    '''
    url = types.InlineKeyboardButton(text="Мои проекты", url=MY_SITE)
    bot.send_message(message.chat.id, 'Автор - @tosha_glyzin\n\n', reply_markup=types.InlineKeyboardMarkup().add(url))


@bot.message_handler(commands=['start'])
def send_welcome(message):
    '''
    Обработка команды старт
    '''
    add_birthday = types.InlineKeyboardButton(text="Запомни мой день рождения...", callback_data="add_birthday")
    keyboard = types.InlineKeyboardMarkup().add(add_birthday)
    bot.send_sticker(message.chat.id, 'CAACAgIAAxkBAAIDzGJcH8H9iLlTVc2itMoRjhlB5SxEAAIMEQACheuhStHnYfS8-vRpJAQ')
    bot.send_message(message.chat.id, mess_start, reply_markup=keyboard)
    id_user = message.chat.id
    name_user = message.chat.first_name
    last_user = message.chat.last_name
    linkname = message.chat.username
    gend = 0
    GENDER = {'М': 1, 'Ж': 2}
    with open(BASE_DIR / 'russian_names.json', encoding='utf-8-sig') as file:
        names = json.load(file)
    for name in names:
        if name['Name'] == name_user:
            gend = GENDER.get(name['Sex'],0)

    defaults = {}
    if gend:
        defaults = {'sex': gend}
    defaults.update({'username':f'{name_user} {last_user}', 'linkname':linkname})
    UserTemplate.objects.update_or_create(id_user=id_user, defaults=defaults)



@bot.message_handler(commands=['setmessage'])
def set_message(message):
    '''
    Обработка команды setmessage.
    Чтение инструкции из файла и отправка сообщения с клавиатурой.
    Поиск пользователя, если есть шаблон в базе. Нужно, чтоб вывести.
    '''
    with open(BASE_DIR / 'setmessage.txt') as file:
            str = file.read()
    bot.send_message(message.chat.id, str, parse_mode='Markdown')
    add_fields = types.InlineKeyboardButton(text="Добавить шаблон", callback_data="add_fields")
    del_fields = types.InlineKeyboardButton(text="Удалить шаблон", callback_data="del_fields")
    add_site = types.InlineKeyboardButton(text="Добавить сайт", callback_data="add_site")
    keyboard = types.InlineKeyboardMarkup().add(add_fields).add(del_fields).add(add_site)
    bot.send_message(message.chat.id, 'Приступаем к настройкам?', reply_markup=keyboard)
    try:
        record = UserTemplate.activated.get(id_user=message.chat.id)
        if record.content:
            bot.send_message(message.chat.id, 'Ваши настройки\n\n'+\
                                                f'{record.content}')
    except:
        pass


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    '''
    Сюда приходят информация о нажатой кнопки, чтобы ее обработать.
    '''
    if call.data == 'add_fields':
        add_fields = bot.send_message(call.message.chat.id, 'Напишите ваш шаблон')
        bot.register_next_step_handler(add_fields, func_add_fields)
    elif call.data == 'add_site':
        add_site = bot.send_message(call.message.chat.id, 'Ссылка на сайт')
        bot.register_next_step_handler(add_site, func_add_site)
    elif call.data == 'del_fields':
        del_fields_yes = types.InlineKeyboardButton(text="Да", callback_data="del_fields_yes")
        del_fields_no = types.InlineKeyboardButton(text="Нет", callback_data="del_fields_no")
        keyboard = types.InlineKeyboardMarkup(row_width=2).add(del_fields_yes, del_fields_no)
        bot.send_message(call.message.chat.id, 'Вы уверенны в своем решение?', reply_markup=keyboard)
    elif call.data == 'del_fields_yes':
        try:
            UserTemplate.activated.filter(id_user=call.message.chat.id).update(content='')
            bot.send_message(call.message.chat.id, 'Шаблон был удален.')
        except:
            bot.send_message(call.message.chat.id, 'Что-то пошло не так...')
            bot.send_sticker(call.message.chat.id, 'CAACAgIAAxkBAAID62JcILu6ONcZpRyLgykthxqwwcqZAAL-EQACqhahSmihRvf9VXWVJAQ')
    elif call.data == 'add_birthday':
        add_birthday = bot.send_message(call.message.chat.id, 'Я слушаю тебя внимательно...\n\nНапиши мне день и отправь.')
        bot.send_sticker(call.message.chat.id, 'CAACAgIAAxkBAAIHeWJqtgJsse8mWr0hz42IOsF8p_O9AAMUAALwo6FKcgFoJr9NzuQkBA')
        bot.register_next_step_handler(add_birthday, func_add_birthday)
    elif call.data == 'set_pass_portfolio':
        def func_setpass_portfolio(message):
            text = message.text.strip()
            profile = get_object_or_404(Profile, telegram=message.from_user.id)
            profile.user.set_password(text)
            profile.user.save()
            bot.send_message(message.from_user.id, 'Пароль был измененн.')
        new_pass = bot.send_message(call.message.chat.id, 'Напишите свой новый пароль')
        bot.register_next_step_handler(new_pass, func_setpass_portfolio)
    elif call.data == 'active_portfolio':
        def func_active_portfoli(message):
            text = message.text.strip()
            profile = get_object_or_404(Profile, keyword=text)
            exist_last_profile = Profile.objects.filter(telegram=message.from_user.id)
            if exist_last_profile:
                bot.send_message(message.from_user.id, 'У вас уже есть профиль.')
                if exist_last_profile.count() == 1:
                    exist_last_profile[0].delete()
            if not profile.telegram and not exist_last_profile:
                User.objects.filter(id=profile.user.id).update(is_active = True)
                Profile.objects.filter(id=profile.id).update(telegram=message.from_user.id, keyword = '')
                bot.send_message(message.from_user.id, 'Профиль успешно активирован.')
        mess = bot.send_message(call.message.chat.id, 'Напишите секретное слово для активации')
        bot.register_next_step_handler(mess, func_active_portfoli)


def func_add_birthday(message):
    if message.text.strip().isdigit() and (int(message.text.strip())<=31 and int(message.text.strip())>0):
        UserTemplate.activated.filter(id_user=message.from_user.id).update(day_user=int(message.text.strip()))
    else:
        bot.send_message(message.from_user.id, 'Должна быть цифра или число')
    add_month = bot.send_message(message.from_user.id, 'А теперь напиши месяц')
    def func_add_birthday_month(message):
        if message.text.strip().isdigit() and (int(message.text.strip())<=12 and int(message.text.strip())>0):
            UserTemplate.activated.filter(id_user=message.from_user.id).update(month_user=int(message.text.strip()))
            bot.send_sticker(message.from_user.id, 'CAACAgIAAxkBAAIHkWJquKJIfkZ-NOkBvKX87udMTx6QAAIeEAACP6egShWnHdcmWstcJAQ')
        else:
            bot.send_message(message.from_user.id, 'Должна быть цифра или число')
    bot.register_next_step_handler(add_month, func_add_birthday_month)


def func_add_site(message):
    '''
    Функия которая принимает ссылку от
    пользователя для белого списка сайтов.
    '''
    link = message.text.strip()
    if not re.search(r'http[s]?://', link):
        add_site = bot.send_message(message.from_user.id, 'Ссылка должна содержать http или https.')
        bot.register_next_step_handler(add_site, func_add_site)
    else:
        bot.send_message(message.from_user.id, 'Ваш запрос на проверке.')
        bot.send_sticker(ME_ID, 'CAACAgIAAxkBAAIDzGJcH8H9iLlTVc2itMoRjhlB5SxEAAIMEQACheuhStHnYfS8-vRpJAQ')
        bot.send_message(ME_ID, f'whitelist\nПользователь @{message.from_user.username} c id{message.from_user.id} '+\
                f'просит внести сайт в белый список: [{link}]\nТвое решение: да или нет?\n\n /setmessage')


def func_add_fields(message):
    '''
    Функция для добавление и обнавления шаблона
    '''
    user_id = message.from_user.id
    username = f'{message.from_user.first_name} {message.from_user.last_name}'
    user_text = message.text
    UserTemplate.objects.update_or_create(id_user=user_id, defaults={'content':user_text,
                                                                    'username':username})
    bot.send_message(user_id, 'Ваши настройки установленны и готовы к тесту!')
    bot.send_message(user_id, 'Установите скрытое поле и ссылку в форме отправления:\n'+\
                     f'*<input type="hidden" name="chat" value="{user_id}">*\n \
                     ```https://puzzle-chats.herokuapp.com/api/genie/send-message/```', parse_mode='Markdown')


@bot.message_handler(content_types=["text"])
def forText(message):
    '''
    Общалка, а таже обработка запроса на внесение в белый список
    '''
    if message.chat.id == ME_ID:
        if hasattr(message.reply_to_message, 'text'):
            msg = message.reply_to_message.text
            if 'whitelist' in msg and 'да' in message.text:
                id_user = re.findall(r'id[0-9]+', msg)[0][2:]
                bot.send_message(id_user, 'Ссылка одобрена.')
                bot.send_sticker(id_user, 'CAACAgIAAxkBAAID3mJcIIqlL1_SVibSll0Y-i64Kp6zAAIeEAACP6egShWnHdcmWstcJAQ')
            elif 'whitelist' in msg and 'нет' in message.text:
                id_user = re.findall(r'id[0-9]+', msg)[0][2:]
                bot.send_message(id_user, 'Ссылка не одобрена.')
                bot.send_sticker(id_user, 'CAACAgIAAxkBAAID52JcIK65leXCLt0izGkds93DAAF4SQACIBIAApQnoEpxDVSZvavjqyQE')
                
    session_client = dialogflow.SessionsClient()
    session = session_client.session_path(DIALOGFLOW_PROJECT_ID, SESSION_ID)
    text_input = dialogflow.TextInput(text=message.text, language_code=DIALOGFLOW_LANGUAGE_CODE)
    query_input = dialogflow.QueryInput(text=text_input)
    response = session_client.detect_intent(session=session, query_input=query_input)
    response_json = MessageToDict(response._pb)
    try:
        isText = response_json["queryResult"]["parameters"].get('isText', '')
        textFull = response_json["queryResult"].get('fulfillmentText', '')
        sticker = response_json["queryResult"]["parameters"].get('sticker', '')
        photo = response_json["queryResult"]["parameters"].get('file_id', '')
        if sticker and textFull:
            if isText:
                resCho = random.choice([sticker, textFull])
                if resCho == sticker:
                    bot.send_sticker(message.chat.id, sticker)
                else:
                    bot.send_message(message.chat.id, textFull)
            else:
                bot.send_message(message.chat.id, textFull)
                bot.send_sticker(message.chat.id, sticker)
        elif textFull and photo:
            bot.send_message(message.chat.id, textFull)
            bot.send_photo(message.chat.id, photo)
        elif not sticker and textFull:
            bot.send_message(message.chat.id, textFull)
        elif not (sticker and textFull):
            bot.send_sticker(message.chat.id, 'CAACAgIAAxkBAAIEmGJdGs2rBhu_YYo2iIVaWoDtje-OAAJnEwACnRWpSmMaehIUz3UxJAQ')
    except:
        pass


@csrf_exempt
@require_http_methods(["GET", "POST"])
def sendMessage(request):
    '''
    Обработка запросов для отправки сообщений от пользователей.
    '''
    chat = ''
    try:
        data = request.POST or json.loads(request.body) or request.GET
        chat = data.get('chat', '').strip()
        user = UserTemplate.activated.get(id_user=chat)
        temp = user.content
        if not temp:
            return HttpResponse(status=400)
        for field, value in data.items():
            temp = temp.replace(f'[{field}]', value)
        temp = re.sub(r'\[\w+\]','',temp).split('\n')
        temp = '\n'.join([item for item in temp if item.strip()])
        bot.send_message(chat, temp, parse_mode='Markdown')
    except:
        bot.send_message(chat, 'Что-то пошло не так...')
        bot.send_sticker(chat, 'CAACAgIAAxkBAAID62JcILu6ONcZpRyLgykthxqwwcqZAAL-EQACqhahSmihRvf9VXWVJAQ')
    return HttpResponse(status=200)