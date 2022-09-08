from datetime import datetime, timedelta
from io import BytesIO
import json
from djangochannelsrestframework.generics import GenericAsyncAPIConsumer, AsyncAPIConsumer
from djangochannelsrestframework.observer.generics import (ObserverModelInstanceMixin, action)
from djangochannelsrestframework.observer import model_observer
from django.shortcuts import get_object_or_404
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from portfolio.models import Message, Room, UserOnline,\
                            Comment, WorkPost, NotifyMsg,\
                            TimeLine, Raiting, UserFollowers,\
                            Profile
from chat.serializers import MessageSerializer, RoomSerializer, \
                            UserSerializer, ListRoomSerializer,\
                            SetViewMessageSerializer, \
                            UserOnlineSerializer, NotifySerializer,\
                            RaitingPostSerializer, CommentLikeSerializer,\
                            NotifyMsgSerializer
import uuid
from django.db.models import Count
from channels.exceptions import StopConsumer
from django.db.models import Q
from portfolio.serializers import MeCommentProfile, TimeLineSerializer,\
                                    CommentSerializer
from asgiref.sync import async_to_sync
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.renderers import JSONRenderer


class BeginMessageConsumer(GenericAsyncAPIConsumer):
    async def connect(self):
        await super().connect()
        if self.scope['user']:
            request_id =  self.scope['user'].id
            dict_headers = dict(self.scope['headers'])
            self.my_ip = dict_headers.get('x-forwarded-for') or self.scope['client'][0]
            await self.add_group('group-user-'+str(request_id))
            self.my_user_ids = await self.my_users_list_in_chats()
            self.my_followers_ids = await self.get_list_my_followers()
            data = await self.notify_data_user()
            await self.send_json({'request_id': f'user-{request_id}', 'data': data})
            user_online = await self.start_user_online_db()
            await self.notify_user_online(user_online)
        else:
            await self.send_json({'error': 401})
            raise StopConsumer()
            
    async def disconnect(self, code):
        if self.scope['user']:
            user_online = await self.end_user_online_db()
            await self.notify_user_online(user_online)
        raise StopConsumer()
    
    @database_sync_to_async
    def is_user_online(self):
        user = self.scope["user"]
        return UserOnline.objects.filter(user=user, channel_name=self.channel_name).exists()
    
    async def receive_json(self, content, **kwargs):
        us_online = await self.is_user_online()
        if not us_online:
            await self.start_user_online_db()
        return await super().receive_json(content, **kwargs)
    
    @database_sync_to_async
    def get_list_my_followers(self):
        '''
        Формирование списка ид подписчиков
        '''
        user =  self.scope['user']
        prof = user.profile_user.get()
        ufs = UserFollowers.follower.through.objects.filter(profile=prof)
        follower_ids = [uf.userfollowers_id for uf in ufs]
        follower_users = UserFollowers.objects.filter(id__in=follower_ids)
        my_followers_ids = [fu.user.id for fu in follower_users]
        return my_followers_ids
    
    @database_sync_to_async
    def get_notify_list_db(self):
        '''
        Формирование своего списка уведомлений.
        '''
        user = self.scope["user"]
        tm = datetime.now() - timedelta(days=3)
        NotifyMsg.objects.filter(dist_user__id=user.id, created__lt=tm, is_view=True).delete()
        ms = NotifyMsg.objects.filter(dist_user__id=user.id).order_by('-created')
        return NotifyMsgSerializer(ms, many=True, context={'scope':self.scope}).data
    @action()
    async def get_notify_list(self, **kwargs):
        '''
        Запрос на получения списка своих уведомлений.
        '''
        notify = await self.get_notify_list_db()
        await self.send_json({
            'data': notify,
            'action': 'get_notify_list'
        })
        
    @database_sync_to_async
    def get_userid_by_type_notify(self, object_id, type_notify, **kwargs):
        '''
        Получить приемника ид пользователя по типу уведомления.
        '''
        class_msg = dict(
            NEW_COMMENT=Comment,
            SET_RAITING=Raiting,
            ADD_LIKE=Comment,
            DEL_LIKE=Comment,
            ADD_LIKE_TIMELINE=TimeLine,
            DEL_LIKE_TIMELINE=TimeLine,
            NEW_COMMENT_TIMELINE=Comment,
            DEL_COMMENT_TIMELINE=Comment
        )
        user = self.scope["user"]
        if type_notify == 'NEW_COMMENT':
            content_object = get_object_or_404(class_msg.get(type_notify), id=object_id)
            if content_object.comments_res.values('id'):
                parent = content_object.comments_res.get()
                if parent.user.user == content_object.project.author:
                    return None, parent.user.user.id
                return content_object.project.author.id, parent.user.user.id
            else:
                if content_object.user.user != content_object.project.author: 
                    return None, content_object.project.author.id
        if type_notify == 'SET_RAITING':
            content_object = get_object_or_404(class_msg.get(type_notify), project__id=object_id, user=user)
            return None, content_object.project.author.id
        elif type_notify in ['ADD_LIKE', 'DEL_LIKE']:
            content_object = get_object_or_404(class_msg.get(type_notify), id=object_id)
            return None, content_object.user.user.id
        elif type_notify in ['ADD_LIKE_TIMELINE', 'DEL_LIKE_TIMELINE']:
            content_object = get_object_or_404(class_msg.get(type_notify), id=object_id)
            return None, content_object.author.id
        elif type_notify == 'NEW_COMMENT_TIMELINE':
            content_object = get_object_or_404(class_msg.get(type_notify), id=object_id)
            if content_object.comments_res.values('id'):
                parent = content_object.comments_res.get()
                if parent.user.user == content_object.time_line.author:
                    return None, parent.user.user.id
                return content_object.time_line.author.id, parent.user.user.id
            else:
                if content_object.user.user != content_object.time_line.author: 
                    return None, content_object.time_line.author.id
        elif type_notify == 'DEL_COMMENT_TIMELINE':
            if kwargs.get('time_line'):
                content_object = get_object_or_404(TimeLine, id=kwargs.get('time_line'))
                if kwargs.get('parent_id'):
                    comm = content_object.comments_timeline.filter(id=kwargs.get('parent_id'))
                    if comm and comm[0].user.user != content_object.author:
                        return comm[0].user.user.id, content_object.author.id
                return None, content_object.author.id
        elif type_notify == 'DEL_COMMENT':
            if kwargs.get('project'):
                content_object = get_object_or_404(WorkPost, id=kwargs.get('project'))
                if kwargs.get('parent_id'):
                    comm = content_object.comments.filter(id=kwargs.get('parent_id'))
                    if comm and comm[0].user.user != content_object.author:
                        return comm[0].user.user.id, content_object.author.id
                return None, content_object.author.id
        return None, None
                
        
    @database_sync_to_async
    def add_notify_msg_db(self, object_id, type_notify):
        '''
        Добавления записи в модель уведомлений.
        '''
        class_msg = dict(
            NEW_COMMENT=Comment,
            SET_RAITING=Raiting,
            ADD_LIKE=Comment,
            DEL_LIKE=Comment,
            ADD_LIKE_TIMELINE=TimeLine,
            DEL_LIKE_TIMELINE=TimeLine,
            NEW_COMMENT_TIMELINE=Comment,
            DEL_COMMENT_TIMELINE=Comment
        )
        list_action_access_db = ['SET_RAITING', 'ADD_LIKE', 'DEL_LIKE', 
                                 'ADD_LIKE_TIMELINE', 'DEL_LIKE_TIMELINE',
                                 'NEW_COMMENT_TIMELINE', 'DEL_COMMENT_TIMELINE']
        if not type_notify in list_action_access_db:
            return False
        user = self.scope["user"]
        dist_users = []
        if type_notify == 'SET_RAITING':
            content_object = get_object_or_404(class_msg.get(type_notify), project__id=object_id, user=user)
            if content_object.project.author.id != user.id:
                list_rait_ids = class_msg.get(type_notify).objects.filter(project__id=object_id)
                if list_rait_ids:
                    NotifyMsg.objects.filter(type_notify=type_notify, 
                                            object_id__in=[id['id'] for id in list_rait_ids.values('id')]).delete()
                dist_users.append(content_object.project.author)
        elif type_notify == 'ADD_LIKE':
            content_object = get_object_or_404(class_msg.get(type_notify), id=object_id)
            if content_object.user:
                if content_object.user.user.id != user.id:
                    list_like = NotifyMsg.objects.filter(type_notify=type_notify, object_id=object_id, src_user=user)
                    if not list_like:
                        dist_users.append(content_object.user.user)
        elif type_notify == 'DEL_LIKE':
            content_object = get_object_or_404(class_msg.get(type_notify), id=object_id)
            if content_object.user:
                if content_object.user.user.id != user.id:
                    return NotifyMsg.objects.filter(type_notify='ADD_LIKE', object_id=object_id, src_user=user).delete()
        elif type_notify == 'ADD_LIKE_TIMELINE':
            content_object = get_object_or_404(class_msg.get(type_notify), id=object_id)
            if content_object.author.id != user.id:
                dist_users.append(content_object.author)
        elif type_notify == 'DEL_LIKE_TIMELINE':
            content_object = get_object_or_404(class_msg.get(type_notify), id=object_id)
            if content_object.author.id != user.id:
                return NotifyMsg.objects.filter(type_notify='ADD_LIKE_TIMELINE', 
                                                object_id=object_id, src_user=user).delete()
        for dist_user in dist_users:
            return NotifyMsg.objects.create(type_notify=type_notify, 
                                    content_object=content_object,
                                    src_user=user,
                                    dist_user=dist_user)
            
    @database_sync_to_async
    def set_view_notify_db(self):
        '''
        Сделать обновления прочитанными.
        '''
        user = self.scope["user"]
        NotifyMsg.objects.filter(dist_user=user).update(is_view=True)
    @action()
    async def set_view_notify(self, **kwargs):
        '''
        Запрос на обновления просмотров по уведомлениям.
        '''
        await self.set_view_notify_db()
        
    @database_sync_to_async
    def notify_msg_online_db(self, object_id, type_notify, **kwargs):
        '''
        Формирование ответа на взаимодействия с постом.
        '''
        class_msg = {
            'NEW_COMMENT': {
                'class': Comment,
                'serializer': MeCommentProfile
            },
            'SET_RAITING': {
                'class': WorkPost,
                'serializer': RaitingPostSerializer
            },
            'ADD_LIKE': {
                'class': Comment,
                'serializer': MeCommentProfile
            },
            'DEL_LIKE': {
                'class': Comment,
                'serializer': MeCommentProfile
            },
            'ADD_LIKE_TIMELINE': {
                'class': TimeLine,
                'serializer': TimeLineSerializer
            },
            'DEL_LIKE_TIMELINE': {
                'class': TimeLine,
                'serializer': TimeLineSerializer
            },
            'NEW_COMMENT_TIMELINE': {
                'class': TimeLine,
                'serializer': TimeLineSerializer
            },
            'DEL_COMMENT_TIMELINE': {
                'class': TimeLine,
                'serializer': TimeLineSerializer
            },
        }
        event = class_msg.get(type_notify)
        if not event:
            return dict()
        if kwargs.get('time_line'):
            content_object = get_object_or_404(event.get('class'), id=kwargs.get('time_line'))
        else:
            content_object = get_object_or_404(event.get('class'), id=object_id)
        serializer_obj = event.get('serializer')(content_object, context={'scope':self.scope})
        return serializer_obj.data
    
    @database_sync_to_async
    def get_comment_from_notify_db(self, **kwargs):
        user = self.scope["user"]
        if kwargs.get('object_id'):
            comment = Comment.activeted.filter(id=kwargs.get('object_id')).exclude(view__user=user)
            if comment and comment[0].time_line:
                comments_timeline = TimeLineSerializer(comment[0].time_line, context={'scope':self.scope}).data.get('comments_timeline')
                time_line = TimeLineSerializer(comment[0].time_line, context={'scope':self.scope}).data.get('id')
                return dict(
                    time_line=time_line,
                    comments_timeline=comments_timeline
                )
        else:
            comment = Comment.activeted.filter(~Q(user__user=user) & 
                                            (Q(project__author=user) | Q(time_line__author=user) |
                                             Q(comments_res__user__user=user)), user__isnull=False)\
                                        .exclude(view__user=user)
            obj_data = MeCommentProfile(comment, many=True, context={'scope':self.scope})
            return obj_data.data                            
    @action()
    async def get_comment_from_notify(self, **kwargs):
        obj_data = await self.get_comment_from_notify_db(**kwargs)
        await self.send_json(dict(
            action='get_comment_from_notify',
            data=obj_data
        ))
    
    @action()
    async def subscribe_on_post(self, project, **kwargs):
        '''
        Подписаться на события поста при переходе на него.
        '''
        if not f'group-post-{project}' in self.groups:
            await self.add_group(f'group-post-{project}')
    @action()
    async def subscribe_off_post(self, project, **kwargs):
        '''
        Отписаться от событий поста при уходе от него.
        '''
        if f'group-post-{project}' in self.groups:
            await self.remove_group(f'group-post-{project}')
            
    @action()
    async def subscribe_on_event_comment(self, event, **kwargs):
        '''
        Подписаться на комментарии конкретного события.
        '''
        if not f'group-event-{event}' in self.groups:
            await self.add_group(f'group-event-{event}')
        data = await self.notify_msg_online_db(event, kwargs.get('type_notify'))
        await self.send_json({'action':'get_comment_event_post', 'data':data})
            
    @action()
    async def subscribe_off_event_comment(self, event, **kwargs):
        '''
        Отписаться от комментариев.
        '''
        if isinstance(event, list):
            for item in event:
                if f'group-event-{item}' in self.groups:
                    await self.remove_group(f'group-event-{item}')
        else:
            if f'group-event-{event}' in self.groups:
                await self.remove_group(f'group-event-{event}')
        
    @database_sync_to_async    
    def get_channel_user_by_id(self, id):
        '''
        Найти канал по ид пользователя.
        '''
        try:
            user_online = UserOnline.objects.get(user__id=id)
            if user_online.is_state:
                return user_online.channel_name
            else:
                return None
        except ObjectDoesNotExist:
            return None
        
    async def send_notify_user_channel(self, object_id, type_notify, **kwargs):
        '''
        Формирует уведомление пользователю по типу события для отправки.
        '''
        list_notify = ['NEW_COMMENT', 'DEL_COMMENT', 'SET_RAITING', 'ADD_LIKE', 'DEL_LIKE', 
                       'ADD_LIKE_TIMELINE', 'DEL_LIKE_TIMELINE', 
                       'NEW_COMMENT_TIMELINE', 'DEL_COMMENT_TIMELINE']
        if type_notify in list_notify:
            dist_user_tuple = await self.get_userid_by_type_notify(object_id, type_notify, **kwargs)
            for dist_user in dist_user_tuple:
                if not dist_user:
                    continue
                channel_name = await self.get_channel_user_by_id(dist_user)
                if channel_name:
                    await self.channel_layer.send(channel_name,{
                        'type': 'add_notify_msg',
                        'data': dict(
                            type_notify=type_notify,
                            action='notify_observer',
                            object_id=object_id
                        )
                    })
    async def add_notify_msg(self, event):
        '''
        Отправляет уведомления по каналу.
        '''
        await self.send_json(event['data'])
        
    
    @database_sync_to_async
    def get_notify_comment_count_db(self):
        '''
        Узнает есть ли не прочитанные комментарии.
        '''
        user = self.scope["user"]
        comment = Comment.activeted.filter(~Q(user__user=user) & 
                                           (Q(project__author=user) | Q(time_line__author=user) |
                                            Q(comments_res__user__user=user)), user__isnull=False)\
                                    .exclude(view__user=user)
        return dict(
            data={
                'not_read_comment': comment.count()
            },
            action='get_notify_comment_count'
        )
    @action()
    async def get_notify_comment_count(self, **kwargs):
        '''
        Запрос на получение непрочитанных комментариев.
        '''
        count_dict = await self.get_notify_comment_count_db()
        await self.send_json(count_dict)
                    
    @action()
    async def notify_msg_online(self, object_id, type_notify, **kwargs):
        '''
        Отправка сообщений кто смотрит одинаковый пост.
        Сохранение событий в БД.
        Отправка уведомлений конкретному пользователю.
        '''
        user = self.scope["user"]
        await self.add_notify_msg_db(object_id, type_notify)
        await self.send_notify_user_channel(object_id, type_notify, **kwargs)
        if kwargs.get('project'):
            await self.channel_layer.group_send(f'group-post-{kwargs["project"]}',{
                'type': 'send_notify_msg_online',
                'event': type_notify,
                'from_user': user.id,
                'object_id': object_id,
                'kwargs': kwargs
            })
        else:
            list_action = ['NEW_COMMENT_TIMELINE', 'DEL_COMMENT_TIMELINE']
            data = {
                'type': 'send_notify_msg_online',
                'event': type_notify,
                'from_user': user.id,
                'object_id': object_id,
                'kwargs': kwargs
            }
            if type_notify in list_action:
                if kwargs.get('time_line'):
                    await self.channel_layer.group_send(f'group-event-{kwargs["time_line"]}', data)
            else:
                tuble_dist_user = await self.get_userid_by_type_notify(object_id, type_notify, **kwargs)
                for dist_user in tuble_dist_user:
                    channel_name = await self.get_channel_user_by_id(dist_user)
                    if channel_name:
                        await self.channel_layer.send(channel_name, data)
                        
    async def send_notify_msg_online(self, event):
        '''
        Здесь пользователь подписанный на пост получает уведомление.
        list_exclude = ['DEL_COMMENT']
        '''
        list_action = ['NEW_COMMENT', 'SET_RAITING', 'DEL_LIKE', 'ADD_LIKE', 
                       'ADD_LIKE_TIMELINE', 'DEL_LIKE_TIMELINE', 'NEW_COMMENT_TIMELINE',
                       'DEL_COMMENT_TIMELINE']
        serializer_obj = {'id': event['object_id']}
        if event.get('kwargs').get('project'):
            serializer_obj['project'] = event.get('kwargs').get('project')
        if event.get('kwargs').get('time_line'):
            serializer_obj['time_line'] = event.get('kwargs').get('time_line')
        if event['event'] in list_action:
            serializer_obj = await self.notify_msg_online_db(event['object_id'], event['event'], **serializer_obj)
        data = {
            'action': 'SENDED_EVENT',
            'data': serializer_obj,
            'from_user': event['from_user'],
            'event': event['event']
        }
        await self.send_json(data)
        
    @database_sync_to_async
    def notify_data_user(self):
        '''
        Поиск уведомлений при соединение.
        Не прочитанные сообщения, комментарии, уведомления.
        '''
        user = self.scope["user"]
        not_read_rooms = Room.objects.filter(users__in=[user])\
                                    .exclude(name='room-user-'+str(user.id))
        not_read_msg = 0                            
        for room in not_read_rooms:
            msgroom = room.messages.order_by('created').last()
            if msgroom:
                if not msgroom.is_view.filter(user=user).count() and msgroom.user != user:
                    not_read_msg += 1  
        comment = Comment.activeted.filter(~Q(user__user=user) & 
                                           (Q(project__author=user) | Q(time_line__author=user) | 
                                            Q(comments_res__user__user=user)), user__isnull=False)\
                                    .exclude(view__user=user)
        notify = NotifyMsg.objects.filter(dist_user=user, is_view=False).count()
        return dict(not_read_msg=not_read_msg, 
                    not_read_comment=comment.count(), 
                    not_read_notify=notify)                                      
            
    @database_sync_to_async 
    def being_message_db(self, room, text, parent=None):
        '''
        Создания сообщений в БД.
        '''
        user = self.scope["user"]
        msg = None
        if parent:
            parent = get_object_or_404(Message, id=parent)
            msg = Message.objects.create(room=room, text=text, user=user, parent=parent)
        else:
            msg = Message.objects.create(room=room, text=text, user=user)
        return dict(data=MessageSerializer(msg, context={'scope': self.scope}).data, action='created_message')
    @action()
    async def being_message(self, text, to_username=None, 
                            name_room=None, parent=None, **kwargs):
        '''
        Написать сообщение.
        '''
        room = None
        if name_room:
            room = await self.get_room_by_name_db(name_room)
        if not room:
            room = await self.create_or_get_room_db(to_username)
        new_msg_json = await self.being_message_db(room, text, parent)
        list_channels, id_room = await self.list_channels_by_msg(new_msg_json['data']['id'])
        for channel in list_channels:
            await self.channel_layer.send(channel, {
                'type': 'send.new.msg',
                'new_msg': new_msg_json
            })
    async def send_new_msg(self, event):
        await self.send_json(event['new_msg'])
    
    @database_sync_to_async
    def list_channels_by_msg(self, id_msg):
        '''
        Формирование списка каналов по конкретой комнате с сообщениями.
        '''
        list_channels = []
        users_msg = Message.objects.get(id=id_msg).room.users.values('id')
        id_room = Message.objects.get(id=id_msg).room.id
        users_msg = [item['id'] for item in users_msg]
        if not self.scope['user'].id in users_msg:
            return list_channels
        for user_id in users_msg:
            list_us_online = UserOnline.objects.filter(user__id=user_id, is_state=True)
            if list_us_online:
                list_channels.append(list_us_online[0].channel_name)
        return list_channels, id_room
    
    async def notify_view_msg(self, id_msg):
        '''
        Отправка по каналам сообщения для пользователей в комнате.
        '''
        list_channels, id_room = await self.list_channels_by_msg(id_msg)
        for channel in list_channels:
            await self.channel_layer.send(channel, {
                'type': 'send.view.msg',
                'id_msg': id_msg,
                'id_room': id_room
            })
    async def send_view_msg(self, event):
        await self.send_json({'viewed_msg': {'id_msg': event["id_msg"], 
                                            'id_room': event["id_room"]},
                               'action': 'viewed_msg'})
        
    @database_sync_to_async
    def set_view_message_db(self, id_msg):
        '''
        Установить знак просмотренного сообщения для пользователя 
        '''
        data = {
            'object_id': id_msg,
            'user': self.scope['user'].id
        }
        obj_serial = SetViewMessageSerializer(data=data)
        if obj_serial.is_valid():
            obj_serial.save()
        
    @action()    
    async def set_view_message(self, id_msg, **kwargs):
        '''
        Запрос на установку знака просмотра и 
        отправка всем в комнате, что я смотрел сообщения.
        '''
        await self.set_view_message_db(id_msg)
        await self.notify_view_msg(id_msg)
        
        
    @database_sync_to_async 
    def get_list_room_user_db(self, user):
        '''
        Получение списка чата по пользователю.
        '''
        rooms = Room.objects.filter(users__in=[user])
        return rooms
    
    @database_sync_to_async 
    def get_room_serializer(self, rooms, many=False):
        '''
        Сериализация списка чатов или одного чата
        '''
        if many:
            rooms = ListRoomSerializer(rooms, many=many, context={'scope': self.scope}).data
        else:
            rooms = RoomSerializer(rooms, context={'scope': self.scope}).data
        return rooms
    
    @action()
    async def get_list_room(self, **kwargs):
        '''
        Получения списка чатов
        '''
        user = self.scope["user"]
        self.my_user_ids = await self.my_users_list_in_chats()
        rooms = await self.get_list_room_user_db(user)
        rooms = await self.get_room_serializer(rooms, many=True)
        await self.send_json({'data': rooms, 'action': 'get_list_room'})
        
    @action()
    async def get_room_message(self, name_room, **kwargs):
        '''
        Получение сообщений в одном чате
        '''
        room = await self.get_room_by_name_db(name_room)
        room = await self.get_room_serializer(room)
        await self.send_json({'data': room, 'action': 'get_room_message'})
        
    @database_sync_to_async 
    def get_room_by_name_db(self, name_room):
        '''
        Получение чата по названию.
        '''
        user = self.scope["user"]
        room = get_object_or_404(Room, name=name_room, users__in=[user])
        return room
    
    @database_sync_to_async
    def list_channels_by_room(self, id_room):
        '''
        Получение списка пользовательских каналов по ид комнате.
        '''
        list_channels = []
        users_room = Room.objects.get(id=id_room).users.values('id')
        users_msg = [item['id'] for item in users_room]
        if not self.scope['user'].id in users_msg:
            return list_channels
        for user_id in users_msg:
            list_us_online = UserOnline.objects.filter(user__id=user_id, is_state=True)
            if list_us_online:
                list_channels.append(list_us_online[0].channel_name)
        return list_channels
    
    @database_sync_to_async
    def delete_messages_db(self, room, user):
        return Message.objects.filter(room=room, user=user).delete()
    @action()
    async def delete_messages(self, name_room, **kwargs):
        '''
        Удаление всех своих сообщений в чате
        '''
        user = self.scope["user"]
        room = await self.get_room_by_name_db(name_room)
        await self.delete_messages_db(room=room, user=user)
        list_channels = await self.list_channels_by_room(room.id)
        for channel in list_channels:
            await self.channel_layer.send(channel, {
                'type': 'send.delete.messages',
                'user_id': user.id,
                'room_id': room.id
            })
    async def send_delete_messages(self, event):
        await self.send(json.dumps({'data': {'user_id': event["user_id"],
                                            'room_id': event["room_id"]},
                                    'action': 'delete_all_messages'}))
    
    @database_sync_to_async
    def delete_one_messages_db(self, id, user, room_name):
        return Message.objects.filter(user=user, id=id, room__name=room_name).delete()
    @action()
    async def delete_one_message(self, msg_id, room_name, **kwargs):
        '''
        Удаление одно свое сообщение
        '''
        user = self.scope["user"]
        room = await self.get_room_by_name_db(room_name)
        await self.delete_one_messages_db(id=msg_id, user=user, room_name=room.name)
        list_channels = await self.list_channels_by_room(room.id)
        for channel in list_channels:
            await self.channel_layer.send(channel, {
                'type': 'send_delete_one_messages',
                'msg_id': msg_id,
                'room_id': room.id
            })
    async def send_delete_one_messages(self, event):
        await self.send_json({'data': {'msg_id': event["msg_id"],
                                            'room_id': event["room_id"]},
                                    'action': 'delete_one_message'})
    
    @database_sync_to_async
    def edit_my_message_db(self, msg_id, text, room_name):
        return Message.objects.filter(id=msg_id, room__name=room_name).update(text=text)    
    @action()
    async def edit_my_message(self, msg_id, text, room_name, **kwargs):
        '''
        Редактирование своего сообщения
        '''
        room = await self.get_room_by_name_db(room_name)
        list_channels = await self.list_channels_by_room(room.id)
        await self.edit_my_message_db(msg_id, text, room.name)
        for channel in list_channels:
            await self.channel_layer.send(channel, {
                'type': 'send_edit_message',
                'msg_id': msg_id,
                'room_id': room.id,
                'text': text
            })
    async def send_edit_message(self, event):
        await self.send_json({'data': {'msg_id': event["msg_id"],
                                       'room_id': event["room_id"],
                                       'text': event["text"]},
                              'action': 'edited_message'})
        
    @database_sync_to_async
    def get_serializer_user(self, user):
        return UserSerializer(user).data
    
    @action()
    async def leave_from_room(self, name_room, is_delete_msg=False, **kwargs):
        '''
        Покинуть чат или покинуть чат и удалить свои сообщения.
        Если в чате никого нет, то чат полностью удаляется 
        вместе с сообщениями.
        '''
        user = self.scope["user"]
        room = await self.get_room_by_name_db(name_room)
        list_channels = await self.list_channels_by_room(room.id)
        list_channels.remove(self.channel_name)
        await database_sync_to_async(room.users.remove)(user)
        count = await database_sync_to_async(room.users.count)()
        if not count:
            await database_sync_to_async(room.delete)()
        elif is_delete_msg:
            await self.delete_messages_db(room=room, user=user)
        if count:
            for channel in list_channels:
                await self.channel_layer.send(channel, {
                    'type': 'send_leave_from_room',
                    'room_id': room.id,
                })
    async def send_leave_from_room(self, event):
        await self.send_json({'data': {'room_id': event['room_id']}, 
                              'action': 'leave_from_room'})
        
        
    @database_sync_to_async 
    def create_or_get_room_db(self, to_username=None):
        '''
        Создания / получения своего чата или диалога.
        Выполняется из анкеты пользователя.
        '''
        user = self.scope["user"]
        to_username = None if self.scope["user"].username == to_username else to_username
        if to_username:
            friend = get_object_or_404(User, is_active=True, username=to_username)
            room = Room.objects\
                .annotate(user_count=Count('users'))\
                .filter(user_count=2)\
                .filter(users__id__in=[friend.id])\
                .filter(users__id__in=[user.id])
        else:
            room = Room.objects.filter(name=f'room-user-{user.id}')
        if not room:
            if to_username:
                my_uuid = uuid.uuid4()
                name_room = str(my_uuid)
                room = Room.objects.create(name=name_room)
                room.users.add(user, friend)
                self.my_user_ids.append(friend.id)
            else:
                room = Room.objects.create(name=f'room-user-{user.id}', host=user)
                room.users.add(user)
            return room
        return room[0]
    
    
    @database_sync_to_async
    def my_users_list_in_chats(self):
        '''
        Формирование списка из ид с кем я общаюсь.
        '''
        user = self.scope["user"]
        my_rooms = Room.objects.filter(users__in=[user])
        list_user_ids = []
        for room in my_rooms:
            for room_user in room.users.all().exclude(id=user.id):
                if not room_user.id in list_user_ids:
                    list_user_ids.append(room_user.id)
        return list_user_ids
    
    @database_sync_to_async
    def list_channels_by_ids(self, list_user_ids):
        my_users = UserOnline.objects.filter(user__id__in=list_user_ids, is_state=True)
        return [item.channel_name for item in my_users]
    
    @database_sync_to_async
    def serializer_online(self, instance):
        return dict(data=UserOnlineSerializer(instance).data, action='user_state')
    
    async def notify_user_online(self, user_online):
        list_channels = await self.list_channels_by_ids(self.my_user_ids)
        serializer_data = await self.serializer_online(user_online)
        for channel in list_channels:
            await self.channel_layer.send(channel, {
                'type': 'send_online_user',
                'online': serializer_data
            })
    async def send_online_user(self, event):
        await self.send_json(event['online'])
    
    @database_sync_to_async 
    def start_user_online_db(self):
        user = self.scope["user"]
        try:
            us = UserOnline.objects.get(user=user)
            us.channel_name = self.channel_name
            us.is_state = True
            us.save()
            return us
        except UserOnline.DoesNotExist:
            return UserOnline.objects.create(user=user, channel_name=self.channel_name)
        
    @database_sync_to_async 
    def end_user_online_db(self):
        user = self.scope["user"]
        us = get_object_or_404(UserOnline, user=user)
        us.is_state = False
        us.save()
        return us
    