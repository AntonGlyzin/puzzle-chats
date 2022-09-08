import json
from captcha.models import CaptchaStore
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils import timezone
from django.middleware.csrf import get_token
from datetime import datetime
from rest_framework.response import Response

from bagchat.settings import MY_HOST
from .serializers import UserRegisterSerializer, \
                            ProfileUpdateSerializer, ProfileDetailSerializer,\
                            ProfileUpdatePhotoSerializer
from django.contrib.auth.models import User
from rest_framework.views import APIView
from rest_framework import status
from django.contrib.auth import get_user_model
from .models import Profile
from portfolio.models import Room
import string
import random
from rest_framework_simplejwt.authentication import JWTTokenUserAuthentication
from rest_framework.permissions import IsAuthenticated, BasePermission
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import mixins, viewsets
from rest_framework.parsers import MultiPartParser, JSONParser
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from django.middleware import csrf
import uuid
from channels.consumer import SyncConsumer
from genie.views import checkHolidays
from django.utils import dateformat
import requests
from channels.exceptions import StopConsumer
from asgiref.sync import async_to_sync

class EntryPointTasks(SyncConsumer):
    def test_holidays(self, message):
        checkHolidays()
        raise StopConsumer()

class EntryPointByPass(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0])
        ip = request.META.get('HTTP_X_REAL_IP') or request.META.get('REMOTE_ADDR')\
                                                or request.META.get('HTTP_X_FORWARDED_FOR')
        profile = get_object_or_404(Profile.user_active, user__id=serializer.user.id)
        if ip not in profile.my_ip['ip']:
            profile.my_ip['ip'].append(ip)
            Profile.objects.filter(id=profile.id).update(my_ip=profile.my_ip)
        Profile.objects.filter(id=profile.id).update(last_token=serializer.validated_data['access'])
        return Response(serializer.validated_data, status=status.HTTP_200_OK)
        
class registerUserBag(APIView):
    parser_classes = (JSONParser,)
    def post(self, request):
        TYPE_USER= ((1,'Портфолио'), )
        captcha_0 = request.data.pop('captcha_0', None)
        captcha_1 = request.data.pop('captcha_1', None)
        try:
            CaptchaStore.remove_expired()
            captcha_1_low = captcha_1.lower()
            CaptchaStore.objects.get(
                response=captcha_1_low, hashkey=captcha_0, expiration__gt=timezone.now()
            ).delete()
        except:
            return Response(status=status.HTTP_409_CONFLICT, data={'captcha': 'Каптча введена не верно, либо устарела'})
        user = UserRegisterSerializer(data=request.data)
        if user.is_valid():
            passwrd = user.validated_data['password']
            user = get_user_model()(**user.validated_data)
            user.set_password(passwrd)
            user.is_active=False
            user.save()
            ran = ''.join(random.choices(string.ascii_letters + string.digits, k = int(9)))   
            link_profile = [
                {"style":"fa fa-chrome","link":"","name":"Web"},
                {"style":"fa fa-vk","link":"","name":"Vk"},
                {"style":"fa fa-envelope","link":"","name":"Email"},
                {"style":"fa fa-paper-plane","link":"","name":"Telegram"},
                {"style":"fa fa-github","link":"","name":"Github"}
            ]
            ip = request.META.get('HTTP_X_REAL_IP') or request.META.get('REMOTE_ADDR')\
                                                    or request.META.get('HTTP_X_FORWARDED_FOR')
            my_list_ip = {'ip':[ip]}
            crop = '5d26f032932c07b264f6badb0f0ef.jpg.100x100_q85_crop.jpg'
            origin = '5d26f032932c07b264f6badb0f0ef.jpg'
            photo_url = 'https://storage.googleapis.com/antonio-glyzin.appspot.com/portfolio/photo/'
            Profile.objects.create(user=user, type_app=TYPE_USER[0][0], \
                            links=json.dumps(link_profile), keyword=ran, my_ip=my_list_ip,\
                            photo_user=f'{photo_url}{origin}', photo=f'{photo_url}{crop}')
            room = Room.objects.create(name=f'room-user-{user.id}', host=user)
            room.users.add(user)
            return Response(status=status.HTTP_201_CREATED, data={'keyword':ran})
        else:
            return Response(status=status.HTTP_409_CONFLICT, data=user.errors)
        
class IsActiveUserBag(BasePermission):
    def has_permission(self, request, view):
        active = False
        try:
            active = User.objects.get(id=request.user.id).is_active
        except ObjectDoesNotExist:
            active = False
        return True if active else False
    
class checkMyIP(BasePermission):
    def has_permission(self, request, view):
        active = False
        try:
            dict_ip = Profile.user_active.get(user__id=request.user.id).my_ip
            ip = request.META.get('HTTP_X_REAL_IP') or request.META.get('REMOTE_ADDR')\
                                                    or request.META.get('HTTP_X_FORWARDED_FOR')
            active = True if ip in dict_ip['ip'] else False
        except ObjectDoesNotExist:
            active = False
        return True if active else False
    
class MixinAuthBag:
    authentication_classes = [JWTTokenUserAuthentication]
    permission_classes = [IsAuthenticated, IsActiveUserBag, checkMyIP]
    
class UpdateUserBag(MixinAuthBag, APIView):
    parser_classes = (JSONParser,)
    def put(self, request):
        profile = get_object_or_404(Profile.user_active, user__id=request.user.id)
        prof_data = ProfileUpdateSerializer(profile, data=request.data, partial=True, context={'request':request})
        if prof_data.is_valid():
            user_data = prof_data.save()
            user_data = ProfileDetailSerializer(user_data).data
            return Response(status=status.HTTP_200_OK, data=user_data)
        return Response(status=status.HTTP_400_BAD_REQUEST)
    
class UpdateUserPhotoBag(MixinAuthBag, APIView):
    parser_classes = (MultiPartParser,)
    def post(self, request):
        try:
            user = get_object_or_404(Profile, user__id=request.user.id)
            size_kb = request.data.get('file').size / 1024
            if size_kb > 1024:
                return Response(status=status.HTTP_400_BAD_REQUEST, data={'file':'Размер файла превышает 1 Мб'})
            user = ProfileUpdatePhotoSerializer(user, {'photo':request.data.get('file')})
            if user.is_valid():
                user = user.save()
                user = ProfileDetailSerializer(user).data
                return Response(status=status.HTTP_200_OK, data={'user':user})
        except BaseException as err:
            print(err)
        return Response(status=status.HTTP_400_BAD_REQUEST)
    
    
class DetailUserBag(MixinAuthBag, mixins.RetrieveModelMixin, 
                    viewsets.GenericViewSet):
    queryset = Profile.user_active
    serializer_class = ProfileDetailSerializer
    # lookup_field = 'user__username'
    def get_object(self):
        user = get_object_or_404(Profile.user_active, user__id=self.request.user.id)
        return user

def add_file_access(request):
    try:
        ip = request.META.get('HTTP_X_REAL_IP') or request.META.get('REMOTE_ADDR')\
                                                            or request.META.get('HTTP_X_FORWARDED_FOR')
        date_time = datetime.today().strftime("%d-%m-%Y %H:%M:%S")
        query = ''+request.META.get('REQUEST_METHOD', '')+' '+request.get_full_path()+'\t\t'+request.META.get('HTTP_USER_AGENT', '')
        str = f'{ip}\t\t{date_time}\t\t{query}\n'
        with open('access-logs.txt', 'a') as file:
            file.write(str)
    except BaseException as err:
                print(err)


def getProtect(request):
    token = get_token(request)
    return JsonResponse({"token":token})


def checkCaptcha(request, *args, **kwargs):
    data = request.GET
    captcha_0 = data.get('captcha_0', '')
    captcha_1 = data.get('captcha_1', '')
    try:
        CaptchaStore.remove_expired()
        captcha_1_low = captcha_1.lower()
        CaptchaStore.objects.get(
            response=captcha_1_low, hashkey=captcha_0, expiration__gt=timezone.now()
        ).delete()
    except:
        return HttpResponse(status=400)

    return HttpResponse(status=200)