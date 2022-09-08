from django.shortcuts import get_object_or_404
from portfolio.models import Message, Room, ViewObject, \
                            UserOnline, NotifyMsg, Raiting,\
                            WorkPost, Comment, TimeLine
from rest_framework import serializers
from django.contrib.auth.models import User
from django.utils import dateformat
from django.utils import timezone
from django.db.models import Q
from datetime import datetime, timedelta
from django.db.models import Avg
from django.core.exceptions import ObjectDoesNotExist

class ActionIPIDSerializer:
    def get_my_id(self):
        if self.context.get('scope'):
            my_id = self.context.get('scope').get('user').id
        return my_id
    def get_my_ip(self):
        if self.context.get('scope'):
            dict_headers = dict(self.context.get('scope')['headers'])
            my_ip = dict_headers.get('x-forwarded-for') or\
                self.context.get('scope')['client'][0]
        return my_ip

class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField('get_full_name')
    photo = serializers.SerializerMethodField('get_photo')
    def get_photo(self, obj):
        return obj.profile_user.get().photo.name
    def get_full_name(self, obj):
        return obj.get_full_name()
    class Meta:
        model = User
        fields = ['id', 'username', 'full_name', 'photo']
        
        
class NotifySerializer(serializers.ModelSerializer):
    # dist = serializers.SerializerMethodField('get_dist')
    dist_user = UserSerializer()
    user = UserSerializer()
    class Meta:
        model = NotifyMsg
        exclude = []
        depth = 1
    # def get_dist(self, obj):
    #     if obj.content_type.model == 'comment':
    #         UserOnline.objects.filter(id=obj)
    
        
class MessageSerializer(serializers.ModelSerializer):
    created = serializers.SerializerMethodField('get_created')
    user = UserSerializer()
    is_view = serializers.SerializerMethodField('get_is_view')
    is_edit = serializers.SerializerMethodField('get_is_edit')
    parent = serializers.SerializerMethodField('get_parent')
    class Meta:
        model = Message
        exclude = []
        depth = 1
    def get_parent(self, obj):
        if not self.context.get('list'):
            if obj.parent:
                return MessageSerializer(obj.parent, context={'scope': self.context['scope']}).data
    def get_created(self, obj):
        tz = timezone.get_default_timezone()
        time = obj.created.astimezone(tz).strftime("%H:%M")
        return {'date': dateformat.format(obj.created, 'd E Y'), 'time': time}
    def get_is_view(self, obj):
        if self.context:
            user = self.context['scope']['user']
            if obj.user.id == user.id:
                list_view = obj.is_view.filter(~Q(user=user))
                if list_view:
                    return True
            else:
                list_view = obj.is_view.filter(user=user)
                if list_view:
                    return True
        return False
    def get_is_edit(self, obj):
        return True
        # tz = timezone.get_default_timezone()
        # date = obj.created.astimezone(tz)
        # now_date = datetime.now(tz)
        # if timedelta(days=now_date.day) == timedelta(days=date.day):
        #     return True
        # else:
        #     return False
    
class UserOnlineSerializer(serializers.ModelSerializer):
    last_visit = serializers.SerializerMethodField('get_last_visit')
    def get_last_visit(self, obj):
        tz = timezone.get_default_timezone()
        time = obj.last_visit.astimezone(tz).strftime("%H:%M")
        return {'date': dateformat.format(obj.last_visit, 'd E Y'), 'time': time}
    class Meta:
        model = UserOnline
        fields = ['id', 'user', 'last_visit', 'is_state']
    
class ListRoomSerializer(serializers.ModelSerializer):
    last_message = serializers.SerializerMethodField('get_last_message')
    users = UserSerializer(many=True)
    user_online = serializers.SerializerMethodField('get_user_online')
    def get_user_online(self, obj):
        if obj.users.count() == 2:
            friend = obj.users.filter(~Q(id=self.context['scope']['user'].id))
            us = UserOnline.objects.filter(user=friend[0])
            if us:
                return UserOnlineSerializer(us[0]).data
    class Meta:
        model = Room
        fields = ["id", "name", "users", "last_message", 'user_online']
        depth = 1
        read_only_fields = ["last_message",]
    def get_last_message(self, obj):
        return MessageSerializer(obj.messages.order_by('created').last(), 
                                 context={'scope': self.context['scope'], 'list': True}).data
    
class RoomSerializer(ListRoomSerializer):
    messages = serializers.SerializerMethodField('get_messages')
    host = UserSerializer(read_only=True)
    class Meta:
        model = Room
        fields = ["id", "name", "host", "messages", "users", 'user_online']
        depth = 1
    def get_messages(self, obj):
        return MessageSerializer(obj.messages.order_by('created'), many=True,
                                 read_only=True, context={'scope': self.context['scope']}).data
        
class SetViewMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ViewObject
        fields = ['object_id', 'user']
    def create(self, validated_data):
        object_id = validated_data.pop('object_id')
        content_object = get_object_or_404(Message, id=object_id)
        validated_data['content_object'] = content_object
        return super().create(validated_data)
    

class RaitingPostSerializer(serializers.ModelSerializer):
    raiting = serializers.SerializerMethodField('get_raiting')
    project = serializers.SerializerMethodField('get_project')
    class Meta:
        model = WorkPost
        fields = ['raiting', 'project']
    def get_raiting(self, obj):
        rait_list = Raiting.objects.filter(project__id=obj.id)
        raiting = rait_list.aggregate(Avg('num_rait'))['num_rait__avg']
        count_user = rait_list.count()
        return {'raiting':raiting, 'users':count_user}
    def get_project(self, obj):
        return dict(
            id = obj.id,
            title = obj.title,
            slug = obj.slug,
            author = obj.author.id,
        )
        
class CommentLikeSerializer(ActionIPIDSerializer,
                            serializers.ModelSerializer):
    project = serializers.SerializerMethodField('get_project')
    my_like = serializers.SerializerMethodField('get_mylike')
    class Meta:
        model = Comment
        fields = ['id', 'my_like', 'project']
    def get_mylike(self, obj):
        request_userid = self.get_my_id()
        me_like = obj.likes.filter(user_id=request_userid).exists()
        users_id = obj.likes.values('user_id')
        users = []
        if request_userid:
            for user in users_id:
                user_list = User.objects.filter(id=user['user_id'])
                if not user_list:
                    continue
                username = user_list[0].username
                full_name = user_list[0].get_full_name()
                photo = user_list[0].profile_user.values('photo')[0]['photo']
                users.append({'username':username,
                            'full_name':full_name,
                            'photo':photo})
        return {'likes':obj.likes.count(), 'me_like':me_like, 'users':users}
    def get_project(self, obj):
        return dict(
            id = obj.project.id,
            title = obj.project.title,
            slug = obj.project.slug,
            author = obj.project.author.id,
        )
from portfolio.serializers import MyLikesSerializer
class NotifyMsgSerializer(MyLikesSerializer,
                          serializers.ModelSerializer):
    content_object = serializers.SerializerMethodField('get_notify')
    created = serializers.SerializerMethodField('get_created')
    src_user = UserSerializer()
    def get_created(self, obj):
        tz = timezone.get_default_timezone()
        time = obj.created.astimezone(tz).strftime("%H:%M")
        return {'date': dateformat.format(obj.created, 'd E Y'), 'time': time}
    def get_raiting(self, obj):
        return RaitingPostSerializer(obj).data.get('raiting')
    def get_notify(self, obj):
        class_msg = dict(
            NEW_COMMENT=Comment,
            SET_RAITING=Raiting,
            ADD_LIKE=Comment,
            ADD_LIKE_TIMELINE=TimeLine
        )
        try:
            if obj.type_notify == 'SET_RAITING':
                content_object = class_msg.get(obj.type_notify).objects.get(id=obj.object_id)
                raiting = self.get_raiting(content_object.project)
                return dict(
                    type_notify=obj.type_notify,
                    project=dict(
                            project_id=content_object.project.id,
                            project_title=content_object.project.title,
                            project_url=content_object.project.get_absolute_url()
                    ),
                    raiting=raiting
                )
            if obj.type_notify == 'ADD_LIKE':
                content_object = class_msg.get(obj.type_notify).objects.get(id=obj.object_id)
                mylike = self.get_mylike(content_object)
                if content_object.project:
                    return dict(
                        id_comment=content_object.id,
                        type_notify=obj.type_notify,
                        project=dict(
                            project_id=content_object.project.id,
                            project_title=content_object.project.title,
                            project_url=content_object.project.get_absolute_url()
                        ),
                        mylike=mylike
                    )
            if obj.type_notify == 'ADD_LIKE_TIMELINE':
                content_object = class_msg.get(obj.type_notify).objects.get(id=obj.object_id)
                mylike = self.get_mylike(content_object)
                return dict(
                    id_comment=content_object.id,
                    type_notify=obj.type_notify,
                    time_line=content_object.get_query_url,
                    mylike=mylike
                )
        except ObjectDoesNotExist as err:
            print(err)
    class Meta:
        model = NotifyMsg
        fields = ['id', 'src_user', 'content_object', 'created', 'is_view']