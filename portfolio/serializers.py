import json
from django.http import Http404
from rest_framework import serializers
from .models import WorkPost, Comment, \
                    TimeLine, Raiting, LikeObject,\
                    ViewObject, UserFollowers, NotifyMsg
from base.models import Profile, MySkils
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
import io
from django.utils.text import slugify
from django.core.exceptions import PermissionDenied
from django.db.models import Avg
from rest_framework.exceptions import ParseError, NotFound
from django.utils.translation import gettext_lazy as _

class GetMenuSerializer(serializers.ModelSerializer):
    class Meta:
        model = MySkils
        fields = ['id', 'name', 'slug', ]
             
        
class ResCommentSerializer(serializers.RelatedField):
    def to_representation(self, value):
        comm = value.filter(active=True)
        return CommentSerializer(comm, context = self.context, many=True).data
        
class UserPhotoCommentSerializer(serializers.RelatedField):
    def to_representation(self, value):
        return {'id':value.id, 
                'photo':value.photo.name, 
                'full_name': value.user.get_full_name(), 
                'username': value.user.username
                }
        
class ActionIPIDSerializer:
    def get_my_id(self):
        if self.context.get('request'):
            my_id = self.context.get('request').user.id
        elif self.context.get('scope'):
            my_id = self.context.get('scope').get('user').id
        return my_id
    def get_my_ip(self):
        if self.context.get('request'):
            my_ip = self.context['request'].META.get('HTTP_X_REAL_IP')\
                or self.context['request'].META.get('REMOTE_ADDR')\
                or self.context['request'].META.get('HTTP_X_FORWARDED_FOR')
        elif self.context.get('scope'):
            dict_headers = dict(self.context.get('scope')['headers'])
            my_ip = dict_headers.get('x-forwarded-for') or\
                self.context.get('scope')['client'][0]
        return my_ip
    
class MyLikesSerializer(ActionIPIDSerializer,
                        serializers.Serializer):
    my_like = serializers.SerializerMethodField('get_mylike')
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
    
class MyViewSerializer(ActionIPIDSerializer, 
                       serializers.Serializer):
    view = serializers.SerializerMethodField('get_view')
    def get_view(self, obj):
        request_userid = self.get_my_id()
        me_view = obj.view.filter(user__id=request_userid).exists()
        if not me_view:
            ip = self.get_my_ip()
            if ip in obj.ip_view['ip'] and not request_userid:
                me_view = True
        count_user = obj.view.count()
        count_ip = len(obj.ip_view['ip'])
        count_view = count_ip if count_ip > count_user else count_user
        return {'my_view':me_view, 'view':count_view}
    
class CommentSerializer(MyViewSerializer,
                        MyLikesSerializer,
                        serializers.ModelSerializer):
    is_me_comment = serializers.SerializerMethodField('me_comments')
    is_me_project = serializers.SerializerMethodField('me_project')
    parent = serializers.SerializerMethodField('get_parent')
    project_id = serializers.SerializerMethodField('get_project_id')
    response = ResCommentSerializer(read_only=True)
    user = UserPhotoCommentSerializer(read_only=True)
    timeline_id = serializers.SerializerMethodField('get_timeline_id')
    def get_timeline_id(self, obj):
        if obj.time_line:
            return obj.time_line.id
    def get_project_id(self, obj):
        if obj.project:
            return obj.project.id
    def get_parent(self, obj):
        list_res = obj.comments_res.values('id')
        if list_res:
            return list_res[0]
    def me_project(self, obj):
        try:
            if not obj.project:
                return None
            my_id = self.get_my_id()
            if obj.project.author.id == my_id:
                return True
        except BaseException as err:
            print(err)
    def me_comments(self, obj):
        try:
            request_userid = self.get_my_id()
            item_userid = getattr(obj.user.user, 'id', '') \
                        if getattr(obj.user, 'id', '') else ''
        except BaseException as err:
            print(err)
        comments = True if request_userid == item_userid else False
        return comments
    class Meta:
        model = Comment
        fields = ['id', 'name', 'body', 'get_date', 'is_me_comment',\
                'response', 'user', 'my_like', 'view', 'is_me_project', 'parent',\
                'project_id', 'timeline_id']
        
class TimeLineSerializer(MyViewSerializer,
                         MyLikesSerializer,
                         serializers.ModelSerializer):
    project = serializers.SlugRelatedField(slug_field='slug', read_only=True,)
    blog = serializers.SlugRelatedField(slug_field='slug', read_only=True,)
    photo_author = serializers.SerializerMethodField('get_photo_author')
    comments_timeline = serializers.SerializerMethodField('get_comments')
    mytags = serializers.SerializerMethodField('get_tags')
    username = serializers.SerializerMethodField('get_username')
    viewer = serializers.SerializerMethodField('get_viewer')
    show_comment = serializers.SerializerMethodField('get_show_comment')
    def get_show_comment(self, obj):
        if self.context.get('request'):
            event = self.context['request'].query_params.get('event')
            if event and obj.id == int(event):
                return True
        return False
    def get_viewer(self, obj):
        request_userid = self.get_my_id()
        is_my_event = True if obj.author.id == request_userid else False
        if request_userid:
            return {'id':request_userid, 'is_my_event': is_my_event}
    def get_username(self, obj):
        return obj.author.username
    def get_tags(self, obj):
        ls = [item for item in obj.skils.values('id', 'name', 'slug')]
        return ls
    def get_comments(self, obj):
        comments = Comment.activeted.filter(time_line__id = obj.id, comments_res__isnull=True).order_by('created')
        return CommentSerializer(comments, many=True, context = self.context).data
    def get_photo_author(self, obj):
        profile = get_object_or_404(Profile.user_active, user__id=obj.author.id)
        return profile.photo.name
    class Meta:
        model = TimeLine
        fields = ['id', 'get_author', 'username', 'content', 'project', \
                'blog', 'get_date', 'photo_author', 'mytags', \
                'comments_timeline', 'viewer', 'my_like', 'view', 'show_comment']
        
class ResProfileSerializer(serializers.RelatedField):
    def to_representation(self, value):
        comm = value.filter(active=True)
        return MeCommentProfile(comm, context = self.context, many=True).data
        
        
class MeCommentProfile(CommentSerializer):
    project = serializers.SerializerMethodField('get_project')
    response = ResProfileSerializer(read_only=True)
    time_line = serializers.SerializerMethodField('get_time_line')
    def get_time_line(self, obj):
        if obj.time_line:
            return obj.time_line.get_query_url
    def get_project(self, obj):
        if obj.project:
            id = obj.project.id
            name = obj.project.title
            slug = obj.project.get_absolute_url()
            return {'id':id, 'title':name, 'slug':slug }
    class Meta:
        model = Comment
        fields = ['id', 'name', 'body', 'get_date', 'is_me_comment',\
                'response', 'user', 'project', 'my_like', 'view', \
                'is_me_project', 'parent', 'project_id', 'time_line', 'timeline_id']

class MyTagsSerializer(serializers.ModelSerializer):
    class Meta:
        model = MySkils
        fields = '__all__'

class BagsListSerializer(serializers.ModelSerializer):
    skils = MyTagsSerializer(many=True, read_only=True)
    count_viewers = serializers.SerializerMethodField('get_count_viewers')
    count_comments = serializers.SerializerMethodField('get_count_comments')
    def get_count_comments(self, obj):
        return obj.comments.filter(time_line=None, active=True).exclude(name='', body='').count()
    def get_count_viewers(self, obj):
        return len(obj.viewers['ip'])
    class Meta:
        model = WorkPost
        fields = ['id', 'title', 'get_absolute_url', 'slug', 'link', 'skils', \
                'get_author', 'get_tranc_content','get_date', 'get_username',\
                'count_viewers', 'count_comments']
        
class BagsDetailSerializer(serializers.ModelSerializer):
    skils = MyTagsSerializer(many=True, read_only=True)
    comments = serializers.SerializerMethodField('get_comments')
    viewer = serializers.SerializerMethodField('get_viewer')
    raiting = serializers.SerializerMethodField('get_raiting')
    count_viewers = serializers.SerializerMethodField('get_count_viewers')
    count_comments = serializers.SerializerMethodField('get_count_comments')
    list_posts = serializers.SerializerMethodField('get_list_posts_blog')
    type_content = serializers.SerializerMethodField('get_type_post')
    def get_type_post(self, obj):
        return obj.type_content
    def get_list_posts_blog(self, obj):
        posts = TimeLine.activeted.filter(project__id=obj.id, blog__isnull=False)\
                                    .values('project__id')\
                                    .values('blog__id', 'blog__title', 'blog__slug')\
                                    .order_by('blog__date_created')
        return dict(posts=posts, count_posts=posts.count())
    def get_count_comments(self, obj):
        return obj.comments.filter(time_line=None, active=True).count()
    def get_count_viewers(self, obj):
        ip = self.context['request'].META.get('HTTP_X_REAL_IP')\
            or self.context['request'].META.get('REMOTE_ADDR')\
            or self.context['request'].META.get('HTTP_X_FORWARDED_FOR')
        if ip not in obj.viewers['ip']:
            obj.viewers['ip'].append(ip)
            WorkPost.objects.filter(id=obj.id).update(viewers=obj.viewers)
        return len(obj.viewers['ip'])
    def get_raiting(self, obj):
        rait_list = Raiting.objects.filter(project__id=obj.id)
        raiting = rait_list.aggregate(Avg('num_rait'))['num_rait__avg']
        count_user = rait_list.count()
        return {'raiting':raiting, 'users':count_user}
    def get_viewer(self, obj):
        request_userid = self.context.get('request', []).user.id
        if request_userid:
            user_pofile = Profile.user_active.filter(user__id=request_userid)
            if user_pofile:
                item_full_name = user_pofile[0].user.get_full_name()
                return {'id':request_userid, 'name':item_full_name}
    def get_comments(self, obj):
        comments = Comment.activeted.filter(project__id = obj.id, comments_res__isnull=True).order_by('-created', )
        return CommentSerializer(comments, many=True, context = self.context).data
    class Meta:
        model = WorkPost
        fields = ['id','title', 'slug', 'link', 'skils', 'get_author', \
                'content', 'comments','get_date', 'viewer', 'get_username', \
                'key_words', 'description', 'raiting', 'comment_push', 'count_viewers',\
                'count_comments', 'list_posts', 'type_content']
        
class BagsCreateBlogSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkPost
        fields = ['id','title', 'slug', 'photo', 'skils', 'content', 'type_content',\
                'key_words', 'description', 'get_absolute_url', 'link', 'is_published', 'comment_push']
    def create(self, validated_data):
        user = get_object_or_404(User, id=self.context['request'].user.id)
        str_slug = slugify(validated_data['title'], allow_unicode=True) + '-by-' +slugify(user.username, allow_unicode=True)
        validated_data['slug'] = str_slug
        validated_data['author'] = user
        return super().create(validated_data)
        
class CreateCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ['id', 'name', 'body', 'ip', 'sess', 'project', 'time_line']
    def create(self, validated_data):
        project = validated_data.get('project')
        if project:
            if not validated_data['project'].comment_push:
                raise PermissionDenied()
        response = self.context['response']
        if response:
            comment_main = get_object_or_404(Comment, id=response)
            # validated_data['child'] = True
            comment_child = Comment.objects.create(**validated_data)
            comment_main.response.add(comment_child.id)
            comment_main.save(force_update=['response'])
            return comment_child
        return super().create(validated_data)
    
class ProfileFormSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField('get_user')
    count_projects = serializers.SerializerMethodField('get_count_project')
    count_posts = serializers.SerializerMethodField('get_count_posts')
    count_events = serializers.SerializerMethodField('get_count_events')
    myskils = serializers.SerializerMethodField('get_myskils')
    links = serializers.SerializerMethodField('get_mylinks')
    project_tags = serializers.SerializerMethodField('get_project_tags')
    blog_tags = serializers.SerializerMethodField('get_blog_tags')
    links_project = serializers.SerializerMethodField('get_links_project')
    is_my_follower = serializers.SerializerMethodField('get_is_my_follower')
    def get_is_my_follower(self, obj):
        is_my_follower = UserFollowers.objects.filter(user__id=self.context['request'].user.id, follower=obj).count()
        return True if is_my_follower else False
    def get_links_project(self, obj):
        projects = obj.user.work_post.filter(type_content=1,
                                             is_published=True,
                                             timeline_project__isnull=False).values_list('id').distinct()
        projects = WorkPost.published.filter(id__in=projects)
        return projects.values('id', 'title')
    def get_tags_project(self, obj, cnt):
        projects = obj.user.work_post.filter(type_content=cnt, is_published=True)
        skils = []
        for projct in projects:   
            for skil in projct.skils.values():
                if skil['slug'] not in skils:
                    skils.append(skil['slug'])
        skils = MySkils.objects.filter(slug__in=skils)
        return skils.values()
    def get_blog_tags(self, obj):
        return self.get_tags_project(obj, 2)
    def get_project_tags(self, obj):
        return self.get_tags_project(obj, 1)
    def get_mylinks(self, obj):
        return json.loads(obj.links)
    def get_myskils(self, obj):
        list_skils = obj.myskils.values()
        max_value = 0
        for item in list_skils:
            count = TimeLine.activeted.filter(skils__name=item['name'], author=obj.user).count()
            item['timeline_count'] = count
            if count > max_value:
                max_value = count
        for item in list_skils:
            if max_value:
                item['percent_timeline'] = int(item['timeline_count']*100 / max_value)
            else:
                item['percent_timeline'] = 0
        return list_skils
    def get_count_events(self, obj):
        return TimeLine.activeted.filter(author=obj.user).count()
    def get_count_posts(self, obj):
        return WorkPost.BlogPublished.filter(author=obj.user).count()
    def get_count_project(self, obj):
        return WorkPost.PortfolioPublished.filter(author=obj.user).count()
    def get_user(self, obj):
        return User.objects.filter(id=obj.user.id)[0].get_full_name()
    class Meta:
        model = Profile
        fields = ['id', 'user', 'myskils', 'photo_user', 'count_projects',\
            'count_posts', 'count_events', 'myskils', 'links', \
            'project_tags', 'blog_tags', 'links_project', 'is_my_follower']
        
        
class ListPostsUserSerializer(serializers.ModelSerializer):
    skils = MyTagsSerializer(many=True, read_only=True)
    raiting = serializers.SerializerMethodField('get_raiting')
    def get_raiting(self, obj):
        rait_list = Raiting.objects.filter(project__id=obj.id)
        raiting = rait_list.aggregate(Avg('num_rait'))['num_rait__avg']
        count_user = rait_list.count()
        return {'raiting':raiting, 'users':count_user}
    class Meta:
        model = WorkPost
        fields = ['id','title', 'slug', 'link', 'skils', 'get_absolute_url', \
                'type_content', 'is_published', 'key_words', 'description',  \
                'date_created', 'comment_push', 'raiting']
        
class SetRaitingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Raiting
        fields = ['project', 'user']
        
class SetLikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LikeObject
        fields = ['object_id', 'user']
    def create(self, validated_data):
        object_id = validated_data.pop('object_id')
        if self.context['request'].data['type'] == 'timeline':
            content_object = get_object_or_404(TimeLine.activeted, id=object_id)
        if self.context['request'].data['type'] == 'comment':
            content_object = get_object_or_404(Comment.activeted, id=object_id)
        validated_data['content_object'] = content_object
        return super().create(validated_data)
    
class ChangeEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeLine
        fields = ['content', 'blog', 'skils']
        
class AddEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeLine
        fields = ['content', 'project', 'blog', 'skils', 'author', 'id']
        
class SetViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = ViewObject
        fields = ['object_id', 'user']
    def create(self, validated_data):
        object_id = validated_data.pop('object_id')
        if self.context['request'].data['type'] == 'timeline':
            content_object = get_object_or_404(TimeLine.activeted, id=object_id)
        if self.context['request'].data['type'] == 'comment':
            content_object = get_object_or_404(Comment.activeted, id=object_id)
        validated_data['content_object'] = content_object
        return super().create(validated_data)
    
class UserFollowerUpdateSerializer(serializers.ModelSerializer):
    def update(self, instance, validated_data):
        if not isinstance(instance[0], UserFollowers):
            raise ParseError(detail=_('instance не является UserFollowers'))
        if not validated_data.get('follower', []):
            raise NotFound(detail=_('Вы не отписались и не подписались'))
        if validated_data.get('user').id == validated_data.get('follower')[0].user.id:
            raise NotFound(detail=_('Нельзя подписываться на самого себя'))
        my_follow = []
        for item in instance[0].follower.values('id'):
            my_follow.append(item['id'])
        if validated_data['follower'][0].id in my_follow:
            my_follow.remove(validated_data['follower'][0].id)
        else:
            my_follow.append(validated_data['follower'][0].id)
        instance[0].follower.set(my_follow)
        return instance[0]
    class Meta:
        model = UserFollowers
        fields = ['user', 'follower', ]
        
class UserDetailFollowSerializer(serializers.RelatedField):
    def get_count_followers(self, user):
        try:
            return UserFollowers.objects.get(user__id=self.context['request'].user.id)\
                                        .follower.filter(user=user).count()
        except UserFollowers.DoesNotExist:
            return 0
    def to_representation(self, value):
        count_project = WorkPost.PortfolioPublished.filter(author=value.user).count()
        count_posts = WorkPost.BlogPublished.filter(author=value.user).count()
        count_followers = self.get_count_followers(value.user)
        return {'id':value.id, 
                'photo':value.photo.name, 
                'full_name': value.user.get_full_name(), 
                'username': value.user.username,
                'count_project': count_project,
                'count_posts': count_posts,
                'count_followers': count_followers
                } 
        
class UserFollowerListSerializer(serializers.ModelSerializer):
    follower = UserDetailFollowSerializer(many=True, read_only=True)
    class Meta:
        model = UserFollowers
        fields = ['id', 'user', 'follower', ]
        
