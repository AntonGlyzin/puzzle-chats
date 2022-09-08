import os
from django.http import HttpResponse
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .serializers import BagsListSerializer, \
                            BagsDetailSerializer, \
                            CreateCommentSerializer, \
                            TimeLineSerializer,\
                            MeCommentProfile, \
                            ProfileFormSerializer,\
                            BagsCreateBlogSerializer,\
                            ListPostsUserSerializer,\
                            SetRaitingSerializer,\
                            SetLikeSerializer,\
                            ChangeEventSerializer,\
                            AddEventSerializer,\
                            CommentSerializer,\
                            SetViewSerializer,\
                            MyLikesSerializer,\
                            UserFollowerUpdateSerializer,\
                            UserFollowerListSerializer
from .models import WorkPost, Comment, TimeLine, \
                    Raiting, LikeObject, ViewObject, UserFollowers
                    
from rest_framework.views import APIView
from captcha.models import CaptchaStore
from bagchat.settings import MEDIA_ROOT, BASE_DIR, TIME_ZONE
from django_filters.rest_framework import DjangoFilterBackend
from django_filters.rest_framework import FilterSet
import django_filters
from rest_framework import filters, status, mixins, viewsets
from rest_framework.pagination import PageNumberPagination
from django.views.decorators.http import require_GET
from django.contrib.auth.models import User
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .models import Profile, MySkils
from base.views import MixinAuthBag
from django.forms.models import model_to_dict
from django.utils.text import slugify
from django.db import IntegrityError
from django.core.exceptions import PermissionDenied
from django.contrib.contenttypes.models import ContentType
from firebase_admin import storage
import base64
import json
from docxtpl import DocxTemplate
from docxtpl import InlineImage
from docx.shared import Mm
from docxtpl import RichText
import jinja2
from datetime import datetime, timedelta
from django.utils import timezone, dateformat
from django.utils.translation import gettext_lazy as _
from base.service import FireBaseStorage
from django.utils.crypto import get_random_string
from django.db.models import Q
from rest_framework.exceptions import NotFound
# Create your views here.

LIMIT_COMMENT_ADMIN = 3
LIMIT_POSTS_BLOG = 3
LIMIT_EVENTS = 3
HOSTPICS = 'https://storage.googleapis.com/antonio-glyzin.appspot.com'
LINK_SITE = 'http://localhost:8080'

class ProfileForm(viewsets.ReadOnlyModelViewSet):
    '''
    Вывод пользовательской акеты по username
    '''
    queryset = Profile.user_active
    serializer_class = ProfileFormSerializer
    lookup_field = 'user__username'

class getMenu(APIView):
    '''
    Формирование меню для зарегистрированного пользователя 
    '''
    def get(self, request):
        
        list_skils = []
        if (request.user.id):
            skils = WorkPost.published.filter(author__id=request.user.id, type_content=2).values('skils__id','skils__name', 'skils__slug')
            for item in skils:
                if item['skils__id'] not in list_skils:
                    list_skils.append(item['skils__id'])
            list_skils = MySkils.objects.filter(id__in=list_skils).values()
        return Response(status=status.HTTP_200_OK, data={'port':[], 'blog':[]})
    
    
class WorkedMePosts(MixinAuthBag, viewsets.ModelViewSet):
    '''
    Выводит статьи в таблицу в адимн панели
    '''
    serializer_class = ListPostsUserSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['date_created', ]
    ordering = ['-date_created', ]
    def get_queryset(self):
        return WorkPost.objects.filter(author__id=self.request.user.id)
    
    
class getSkills(MixinAuthBag, APIView):
    '''
    Получение своих скилов.
    Используется при пользовательском создание скилов.
    '''
    def get(self, request):
        skills = MySkils.objects.all().values()
        return Response(status=status.HTTP_200_OK, data=skills)
    
class getTypeContent(MixinAuthBag, APIView):
    '''
    При создание статьи в админ панели, есть выбор контента
    '''
    def get(self, request):
        type_cont = [
            {'name':'Портфолио', 'code': 1},
            {'name':'Блог', 'code': 2}
        ]
        return Response(status=status.HTTP_200_OK, data=type_cont)
    
class addSkill(MixinAuthBag, APIView):
    '''
    Добавление пользователем скилов в админ панели
    '''
    parser_classes = [JSONParser]
    def post(self, request):
        skill = request.data.get('skill')
        if skill:
            try:
                skill = MySkils.objects.create(name=skill, slug=slugify(skill, allow_unicode=True))
                return Response(status=status.HTTP_200_OK, data=model_to_dict(skill))
            except IntegrityError as err:
                return Response(status=status.HTTP_400_BAD_REQUEST, data={'error': 'Такое умение уже существует'})
        return Response(status=status.HTTP_400_BAD_REQUEST)

# @require_GET
# def robots_txt(request):
#     lines = [
#         "User-Agent: *",
#         f"Sitemap: {MY_HOST}/sitemap.xml",
#         f"Host: {MY_HOST}",
#     ]
#     return HttpResponse("\n".join(lines), content_type="text/plain")

class PaginationComment(PageNumberPagination):
    page_size = LIMIT_COMMENT_ADMIN
    page_size_query_param = 'limit'

class ListMeComment(MixinAuthBag, mixins.ListModelMixin,
                           viewsets.GenericViewSet):
    '''
    Выводит комментарии в админ панели
    '''
    serializer_class = MeCommentProfile
    pagination_class = PaginationComment
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['id', ]
    ordering = ['-id', ]
    def get_queryset(self):
        user_id = self.request.user.id
        comm = Comment.activeted.filter(Q(comments_res__isnull=True) & (Q(project__author__id=user_id) | \
                                        Q(user__user__id=user_id) | Q(time_line__author__id=user_id)) )
        return comm
    
class PaginationPages(PageNumberPagination):
    page_size = LIMIT_POSTS_BLOG
    page_size_query_param = 'limit'
    
class PaginationEvents(PageNumberPagination):
    page_size = LIMIT_EVENTS
    page_size_query_param = 'limit'
    
class RangeFilterEvents(django_filters.FilterSet):
    date = django_filters.DateFromToRangeFilter(field_name='date_created')
    tags = django_filters.CharFilter(field_name='skils__slug')
    project = django_filters.CharFilter(field_name='project')
    class Meta:
        model = TimeLine
        fields = ['date_created', 'tags', 'project']
  
class MixEventViewParams:
    filter_backends = [filters.OrderingFilter, DjangoFilterBackend]
    filterset_class = RangeFilterEvents
    serializer_class = TimeLineSerializer
    ordering_fields = ['date_created', ]
    ordering = ['-date_created', ]
    pagination_class = PaginationEvents
    
class EventViewList(MixEventViewParams,
                    viewsets.ReadOnlyModelViewSet):
    '''
    Вывод событий в общий блок для просмотра
    '''
    def get_queryset(self):
        queryset = TimeLine.activeted
        username = self.request.query_params.get('user')
        if username is not None:
            queryset = queryset.filter(author__username=username)
            return queryset
        raise NotFound()
    
class AddEditEventView(MixinAuthBag, 
                    mixins.CreateModelMixin,
                    mixins.UpdateModelMixin,
                    mixins.DestroyModelMixin,
                    viewsets.GenericViewSet):
    '''
    Добавление и редактирование событий для пользователя
    '''
    queryset = TimeLine.objects.all()
    parser_classes = (JSONParser, )
    def get_object(self):
        obj = get_object_or_404(self.queryset, id=self.kwargs['id'])
        self.check_object_permissions(self.request, obj)
        return obj
    def check_object_permissions(self, request, obj):
        if obj.author.id != request.user.id:
            raise PermissionDenied()
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return AddEventSerializer
        elif self.request.method == 'PUT':
            return ChangeEventSerializer
    def create(self, request, *args, **kwargs):
        request.data['author'] = request.user.id
        post = super().create(request, *args, **kwargs)
        return self.response_object(post.data.get('id'), post.status_code)
    def response_object(self, id, status):
        post = get_object_or_404(self.queryset, id=id)
        post = TimeLineSerializer(post, context={'request': self.request}).data
        return Response(status=status, data=post)
    
class FilterBagList(FilterSet):
    tags = django_filters.CharFilter(field_name='skils__slug')
    class Meta:
        model = WorkPost
        fields = ['tags']
        
class SearchTitleOrContent(filters.SearchFilter):
    def get_search_fields(self, view, request):
        if 'title' in request.query_params:
            return ['$title']
        return super().get_search_fields(view, request)
    
class MixParamBag:
    filter_backends = [DjangoFilterBackend, SearchTitleOrContent, filters.OrderingFilter]
    filter_class = FilterBagList
    search_fields = ['$title', '$content', ]
    ordering_fields = ['date_created', ]
    ordering = ['-date_created', ]
    pagination_class = PaginationPages

class BagMixin(MixParamBag):
    '''
    Вывод контентной части для портфолио и блога
    '''
    lookup_field = 'slug'
    def get_serializer_class(self):
        if self.action == 'list':
            return BagsListSerializer
        elif self.action == "retrieve":
            return BagsDetailSerializer
    def get_queryset(self):
        if 'portfolio' in self.request.path:
            queryset = WorkPost.PortfolioPublished
        elif 'blog' in self.request.path:
            queryset = WorkPost.BlogPublished
        username = self.request.query_params.get('user')
        if username is not None:
            queryset = queryset.filter(author__username=username)
        return queryset
    

class PortfolioViewSet(BagMixin, viewsets.ReadOnlyModelViewSet):
    pass
        
class BlogViewSet(BagMixin, viewsets.ReadOnlyModelViewSet):
    pass
    
class PageViewSet(viewsets.ReadOnlyModelViewSet):
    '''
    Вывод одной статьи
    '''
    lookup_field = 'slug'
    queryset = WorkPost.PagePublished
    serializer_class = BagsDetailSerializer
    
class UpdateComment(MixinAuthBag, mixins.UpdateModelMixin, 
                    viewsets.GenericViewSet):
    '''
    Нужен для удаление комментариев. Удаление пустых родителей.
    '''
    queryset = Comment.activeted
    def update(self, request, *args, **kwargs):
        self.queryset.filter(id=kwargs['id'], user__user__id=request.user.id).delete()
        return Response(status=status.HTTP_200_OK)
    
class CreatePostPortfolio(MixinAuthBag, mixins.UpdateModelMixin,
                          mixins.CreateModelMixin, 
                          mixins.DestroyModelMixin,
                        viewsets.GenericViewSet):
    '''
    Взаимодействия с постом в адимн панели
    '''
    parser_classes = (MultiPartParser, FormParser, JSONParser,)
    serializer_class = BagsCreateBlogSerializer
    queryset = WorkPost.objects.all()
    def create(self, request, *args, **kwargs):
        try:
            post = super().create(request, *args, **kwargs)
            return self.response_object(post.data['id'], status.HTTP_201_CREATED)
        except IntegrityError:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={'error': 'Пост с таким название уже существует'})
    def get_object(self):
        post = get_object_or_404(self.queryset, id=self.request.data['id'])
        self.check_object_permissions(self.request, post)
        return post
    def check_object_permissions(self, request, obj):
        if obj.author.id != request.user.id:
            raise PermissionDenied()
    def update(self, request, *args, **kwargs):
        post = super().update(request, *args, **kwargs)
        return self.response_object(post.data['id'], status.HTTP_200_OK)
    def response_object(self, id, status):
        post = get_object_or_404(self.queryset, id=id)
        post = ListPostsUserSerializer(post).data
        return Response(status=status, data=post)
    
class GetContentForEdit(APIView):
    '''
    Подгрузка содержание поста для редактирования
    '''
    def get(self, request, id):
        post = get_object_or_404(WorkPost, id=id)
        return Response(status=status.HTTP_200_OK, data=post.content)
        
    
class CreateComment(APIView):
    '''
    Создание комментариев, как для зарегистрированных, 
    так и для обычных пользователей
    '''
    parser_classes = (JSONParser, )
    def post(self, request):
        data = request.data
        ip = request.META.get('HTTP_X_REAL_IP') or request.META.get('REMOTE_ADDR')\
                                                        or request.META.get('HTTP_X_FORWARDED_FOR')
        if not request.user.id:
            captcha_0 = data.pop('captcha_0')
            captcha_1 = data.pop('captcha_1')
            try:
                CaptchaStore.remove_expired()
                captcha_1_low = captcha_1.lower()
                CaptchaStore.objects.get(
                    response=captcha_1_low, hashkey=captcha_0, expiration__gt=timezone.now()
                ).delete()
            except:
                return Response(status=status.HTTP_409_CONFLICT)
            sess = request.META.get('HTTP_X_CSRFTOKEN') or ''
            data['sess'] = sess
            item = Comment.activeted.filter(name=data['name'].strip(), project__id=data['project'])
            if item and (item[0].sess != sess):
                return Response(status=status.HTTP_423_LOCKED)
        data['ip'] = ip
        if request.user.id:
            name = get_object_or_404(User, id=request.user.id).get_full_name()
            data['name'] = name
        response = data.pop('response', [])
        serializer = CreateCommentSerializer(data=data, context={'response':response})
        if serializer.is_valid():
            obj = {}
            if request.user.id:
                user = Profile.PortfolioActive.filter(user__id=request.user.id)
                if not user:
                    return Response(status=status.HTTP_401_UNAUTHORIZED)
                serializer.save(active=True, user=user[0])
                my_comm = get_object_or_404(Comment.activeted, id=serializer.data['id'])
                obj = CommentSerializer(my_comm, context={'request':request}).data
            else:
                serializer.save()
            return Response(status=status.HTTP_201_CREATED, data=obj)
        return Response(status=status.HTTP_400_BAD_REQUEST)
    
class SetRaiting(MixinAuthBag, APIView):
    '''
    Установка рейтинга для зарегистрированного пользователя
    '''
    parser_classes = (JSONParser, )
    def post(self, request):
        project = request.data['project']
        raiting = request.data['raiting']
        user = request.user.id
        valid = SetRaitingSerializer(data={'project':project, 'user':user})
        if valid.is_valid():
            project = valid.validated_data['project']
            user = valid.validated_data['user']
            obj, response = Raiting.objects.update_or_create(project=project, user=user, defaults={'num_rait':raiting})
            return Response(status=status.HTTP_200_OK, data={'plus':response})
        return Response(status=status.HTTP_400_BAD_REQUEST)
    

class SetLikes(MixinAuthBag, 
               mixins.CreateModelMixin,
               mixins.DestroyModelMixin,
               viewsets.GenericViewSet):
    '''
    Ставит и удаляет лайки для зарегистрированных 
    '''
    queryset = LikeObject.objects.all()
    serializer_class = SetLikeSerializer
    parser_classes = (JSONParser, )
    def get_likes(self, request, res):
        data = ''
        if request.data['type'] == 'comment':
            object_id = request.data['object_id']
            queryset = Comment.activeted
        if request.data['type'] == 'timeline':
            object_id = request.data['object_id']
            queryset = TimeLine.activeted
        comm = get_object_or_404(queryset, id=object_id)
        data = MyLikesSerializer(comm, context={'request':request}).data
        return Response(status=res.status_code, data=data)
    def create(self, request, *args, **kwargs):
        request.data['user'] = request.user.id
        res = super().create(request, *args, **kwargs)
        return self.get_likes(request, res)
    def get_object(self):
        id_user = self.request.user.id
        object_id = self.request.data['object_id']
        if self.request.data['type'] == 'timeline':
            type = ContentType.objects.get_for_model(TimeLine)
        if self.request.data['type'] == 'comment':
            type = ContentType.objects.get_for_model(Comment)
        object = get_object_or_404(self.queryset, user__id=id_user, object_id=object_id, content_type__pk=type.id)
        return object
    
class getMyPics(MixinAuthBag, APIView):
    '''
    Берет список картинок пользователя из storage
    '''
    def get(self, request):
        username = get_object_or_404(User, id=request.user.id).username
        bucket = storage.bucket()
        newlist_pics = []
        list_avatar = bucket.list_blobs(prefix=f'portfolio/users/{username}/avatar')
        list_portfolio = bucket.list_blobs(prefix=f'portfolio/users/{username}/portfolio')
        for ava in list_avatar:
            split_name = ava.name.split('.')[-2]
            str_name = split_name[-5:]
            if str_name != '_crop':
                newlist_pics.append({'itemImageSrc':ava.name,
                                     'thumbnailImageSrc':ava.name,
                                     'title':split_name.split('/')[-1],
                                     'is_ava': True})
        for pic in list_portfolio:
            split_name = pic.name.split('.')[-2]
            newlist_pics.append({'itemImageSrc':pic.name,
                                'thumbnailImageSrc':pic.name,
                                'title':split_name.split('/')[-1],
                                'is_ava': False})
        return Response(status=status.HTTP_200_OK, data=newlist_pics)
    
class dowloadMyPics(MixinAuthBag, APIView):
    '''
    Для скачаивания файла из адинки
    '''
    def get(self, request):
        file = request.query_params['img'].strip()
        bucket = storage.bucket()
        blob = bucket.blob(file)
        contents = blob.download_as_bytes()
        base64_data = base64.b64encode(contents)
        return Response(status=status.HTTP_200_OK, data=base64_data)
    
class deleteMyPic(MixinAuthBag, APIView):
    '''
    Удаление файла
    '''
    def delete(self, request):
        username = get_object_or_404(User, id=request.user.id).username
        file = request.query_params['img'].strip()
        if file.split('/')[2] != username:
            return Response(status=status.HTTP_403_FORBIDDEN)
        bucket = storage.bucket()
        blob = bucket.blob(file)
        blob.delete()
        data = {}
        if file.split('/')[3] == 'avatar':
            list_avatar = bucket.list_blobs(prefix=f'portfolio/users/{username}/avatar')
            for ava in list_avatar:
                if file in ava.name:
                    ava.delete()
                    user = Profile.objects.filter(user__username=username, photo_user=f'{HOSTPICS}/{file}')
                    if user:
                        crop = '5d26f032932c07b264f6badb0f0ef.jpg.100x100_q85_crop.jpg'
                        origin = '5d26f032932c07b264f6badb0f0ef.jpg'
                        photo_url = 'https://storage.googleapis.com/antonio-glyzin.appspot.com/portfolio/photo/'
                        Profile.objects.filter(user__username=username).update(photo_user=f'{photo_url}{origin}', photo=f'{photo_url}{crop}')
                        data['photo_user'] = f'{photo_url}{origin}'
                        data['photo'] = f'{photo_url}{crop}'
                        return Response(status=status.HTTP_200_OK, data=data)
        return Response(status=status.HTTP_204_NO_CONTENT)
    
class setMyPicAva(MixinAuthBag, APIView):
    '''
    Обнавления картинки профиля из firebase storage
    thumbnailImageSrc = origin
    '''
    parser_classes = (JSONParser, )
    def put(self, request):
        if not request.data['is_ava']:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        bucket = storage.bucket()
        username = get_object_or_404(User, id=request.user.id).username
        list_avatar = bucket.list_blobs(prefix=f'portfolio/users/{username}/avatar')
        data = {}
        for ava in list_avatar:
            split_name = ava.name.split('.')[-2]
            str_name = split_name[-5:]
            if str_name == '_crop':
                if request.data['thumbnailImageSrc'] in ava.name:
                    Profile.user_active.filter(user__id=request.user.id)\
                        .update(photo=f'{HOSTPICS}/{ava.name}', photo_user=f"{HOSTPICS}/{request.data['thumbnailImageSrc']}")
                    data = {
                        'photo': f'{HOSTPICS}/{ava.name}',
                        'photo_user': f"{HOSTPICS}/{request.data['thumbnailImageSrc']}"
                    }
        return Response(status=status.HTTP_200_OK, data=data)
    
class UserResume(MixinAuthBag, APIView):
    '''
    Отдает резюме для сайта. Сохраняет в базе.
    '''
    parser_classes = (JSONParser, )
    def get(self, request):
        resume = get_object_or_404(Profile.user_active, user__id=request.user.id).resume
        return Response(status=status.HTTP_200_OK, data=resume)
    def put(self, request):
        Profile.user_active.filter(user__id=request.user.id).update(resume=request.data)
        return Response(status=status.HTTP_200_OK)
        
class GetDocResum(MixinAuthBag, APIView):
    '''
    Формирует и отдает пользователю резюме
    '''
    def get(self, request):
        doc = DocxTemplate(os.path.join(BASE_DIR, "resum.docx"))
        def get_date(value):
            day = datetime.strptime(value,"%Y-%m-%dT%H:%M:%S.%fZ").strftime("%d")
            mon = datetime.strptime(value,"%Y-%m-%dT%H:%M:%S.%fZ").strftime("%m")
            year = datetime.strptime(value,"%Y-%m-%dT%H:%M:%S.%fZ").strftime("%Y")
            hor = datetime.strptime(value,"%Y-%m-%dT%H:%M:%S.%fZ").strftime("%H")
            tz = datetime(year=int(year), month=int(mon), day=int(day), hour=int(hor)) + timedelta(hours=4)
            return tz
        
        def func_date(value):
            source = RichText("")
            date = get_date(value)
            date = dateformat.format(datetime(day=date.day, year=date.year, month=date.month), 'd E Y')
            source.add(date)
            return source
        
        def split_text(val):
            return val.split('\n')
        
        def get_link(val):
            source = RichText("")
            source.add('Источник',url_id=doc.build_url_id(val), color='#1856af', underline=True)
            return source
        
        def get_inerval_date(vals):
            str = ''
            for i, val in enumerate(vals):
                date = dateformat.format(get_date(val), 'E Y')
                str += " - " + date if i == 1 else date
            str += ' - до настоящего времени' if len(vals) == 1 else ''
            return str
        
        def get_myskils(myskils, user):
            list_skils = myskils.values()
            max_value = 0
            for item in list_skils:
                count = TimeLine.activeted.filter(skils__name=item['name'], author=user.user).count()
                item['timeline_count'] = count
                if count > max_value:
                    max_value = count
            for item in list_skils:
                if max_value:
                    item['percent_timeline'] = int(item['timeline_count']*100 / max_value)
                else:
                    item['percent_timeline'] = 0
            return list_skils
        
        user = get_object_or_404(Profile.user_active, user__id=request.user.id)
        mypath = MEDIA_ROOT
        mypathdoc = os.path.join(mypath, f"generated_doc_{user.user.username}.docx")
        mypathfile = ''
        try:
            bucket = storage.bucket()
            photo_name_path = user.photo_user.replace(HOSTPICS,'')[1:]
            blob = bucket.blob(photo_name_path)
            filename = user.photo_user.split('/')[-1]
            contents = blob.download_as_bytes()
            mypathfile = os.path.join(mypath, user.user.username + filename)
            with open(mypathfile, 'wb') as file:
                file.write(contents)
            img = InlineImage(doc, mypathfile, width=Mm(40))
        except BaseException as err:
            print(err)
            img = ''
            mypathfile = ''
        resume = user.resume
        userWorks = sorted(resume['userWorks'], \
            key=lambda x: x['years'][0] if len(x['years']) else '', reverse=True)
        userStudy = sorted(resume['userStudy'], \
            key=lambda x: x['years'][0] if len(x['years']) else '', reverse=True)
        plusStudy = sorted(resume['plusStudy'], \
            key=lambda x: x['years'][0] if len(x['years']) else '', reverse=True)
        resume['userWorks'] = userWorks
        resume['userStudy'] = userStudy
        resume['plusStudy'] = plusStudy
        full_name = user.user.get_full_name()
        skills = get_myskils(user.myskils.values(), user)
        contact = json.loads(user.links)
        jinja_env = jinja2.Environment()
        jinja_env.filters['date'] = func_date
        jinja_env.filters['split_text'] = split_text
        jinja_env.filters['get_link'] = get_link
        jinja_env.filters['get_inerval_date'] = get_inerval_date
        projects = user.user.work_post.filter(is_published=True, type_content=1).values('title', 'slug')
        for project in projects:
            project['link'] = LINK_SITE + '/portfolio/post/' + project['slug']
        context = { 'img':img, 'contact': contact,
                   'full_name': full_name,
                   'skills': skills,
                   'projects': projects,
                   'resume': resume,
                   'portfolio': f'{LINK_SITE}/card/user/{user.user.username}'}
        doc.render(context, jinja_env)
        doc.save(mypathdoc)
        down_file = ''
        with open(mypathdoc, 'rb') as file:
            down_file = file.read()
        base64_data = base64.b64encode(down_file)
        if mypathfile:
            os.remove(mypathfile)
        os.remove(mypathdoc)
        return Response(status=status.HTTP_200_OK, data={'file':base64_data, 'user':user.user.username})
        
class SetView(mixins.CreateModelMixin,
               viewsets.GenericViewSet):
    '''
    Ставит просмотры для всех 
    '''
    queryset = ViewObject.objects.all()
    serializer_class = SetViewSerializer
    parser_classes = (JSONParser, )
    def create(self, request, *args, **kwargs):
        request.data['user'] = request.user.id
        ip = request.META.get('HTTP_X_REAL_IP')\
            or request.META.get('REMOTE_ADDR')\
            or request.META.get('HTTP_X_FORWARDED_FOR')
        if request.data['type'] == 'comment':
            comm = get_object_or_404(Comment.activeted, id=request.data['object_id'])
            if ip not in comm.ip_view['ip']:
                comm.ip_view['ip'].append(ip)
                Comment.activeted.filter(id=request.data['object_id']).update(ip_view=comm.ip_view)
        elif request.data['type'] == 'timeline':
            comm = get_object_or_404(TimeLine.activeted, id=request.data['object_id'])
            if ip not in comm.ip_view['ip']:
                comm.ip_view['ip'].append(ip)
                TimeLine.activeted.filter(id=request.data['object_id']).update(ip_view=comm.ip_view)
        if request.user.id:
            return super().create(request, *args, **kwargs)
        return Response(status=status.HTTP_201_CREATED)
    
class UserFollowersView(MixinAuthBag,
                        mixins.ListModelMixin,
                        mixins.CreateModelMixin,
                        mixins.UpdateModelMixin,
                        viewsets.GenericViewSet):
    '''
    Сохранение и показ подписок для пользователей
    '''
    parser_classes = (JSONParser, )
    def update(self, request, *args, **kwargs):
        request.data['user'] = request.user.id
        user = self.get_queryset()
        if not user:
            return super().create(request, *args, **kwargs)
        return super().update(request, *args, **kwargs)
    def get_object(self):
        user = UserFollowers.objects.get_or_create(user__id=self.request.user.id)
        return user
    def get_serializer_class(self):
        if self.action == 'update':
            return UserFollowerUpdateSerializer
        elif self.action == 'list':
            return UserFollowerListSerializer
    def get_queryset(self):
        return UserFollowers.objects.filter(user__id=self.request.user.id)
    
class MixListFollowers:
    '''
    Формирование списка подписок для пользователя
    '''
    def get_list_follower(self):
        username = []
        list_follow = UserFollowers.objects.filter(user__id=self.request.user.id)
        for follow in list_follow:
            list_prof = follow.follower.filter()
            for prof in list_prof:
                username.append(prof.user.username)
        return username
    
class FollowPostsMe(MixinAuthBag,
                    MixParamBag,
                    MixListFollowers,
                    mixins.ListModelMixin,
                    viewsets.GenericViewSet):
    '''
    Вывод проектов и постов в подписках
    '''
    serializer_class = BagsListSerializer
    postfix = ['portfolio', 'blog', ]
    def get_queryset(self):
        username = self.get_list_follower()
        posts = []
        if self.kwargs['postfix'] == self.postfix[0]:
            posts = WorkPost.PortfolioPublished.filter(author__username__in=username)
        elif self.kwargs['postfix'] == self.postfix[1]:
            posts = WorkPost.BlogPublished.filter(author__username__in=username)
        username = self.request.query_params.get('user')
        if username is not None:
            posts = posts.filter(author__username=username)
        return posts
    
class FollowEventsMe(MixinAuthBag,
                    MixEventViewParams,
                    MixListFollowers,
                    mixins.ListModelMixin,
                    viewsets.GenericViewSet):
    '''
    Вывод событий в подписках
    '''
    def get_queryset(self):
        queryset = TimeLine.activeted.filter(author__username__in=self.get_list_follower()) 
        username = self.request.query_params.get('user')
        if username is not None:
            queryset = queryset.filter(author__username=username)
        return queryset

class UploadFileToPost(MixinAuthBag, APIView):
    ''''
    Вставка изображений в пост
    '''
    parser_classes = (MultiPartParser,)
    def post(self, request):
        try:
            user = get_object_or_404(User, id=request.user.id)
            size_kb = request.data.get('file').size / 1024
            if size_kb > 1024:
                return Response(status=status.HTTP_400_BAD_REQUEST, data={'file':'Размер файла превышает 1 Мб'})
            ext = "." + request.data.get('file').name.split('.')[-1]
            filename = get_random_string(length=32) + ext
            pathname = f'portfolio/users/{user.username}/portfolio/posts/{filename}'
            bin_file = request.data.get('file').read()
            dist_path = BASE_DIR / MEDIA_ROOT / filename
            with open(dist_path, 'wb') as f:
                f.write(bin_file)
            photo_link = FireBaseStorage.get_publick_link(dist_path, pathname)
            os.remove(dist_path)
            return Response(status=status.HTTP_200_OK, data={'photo_link': photo_link})
        except BaseException as err:
            print(err)
            return Response(status=status.HTTP_400_BAD_REQUEST)

