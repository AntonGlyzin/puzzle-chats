from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Profile
from django.contrib.auth.models import User
import json
from django.shortcuts import get_object_or_404

class UserRegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ['username', 'first_name', 'last_name', 'password', ]
    def validate(self, attrs):
        if not attrs.get('first_name') or  not attrs.get('last_name'):
            raise serializers.ValidationError("Поле *Имя* и *Фамилия* обязательны к заполнению")
        return super().validate(attrs)

class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ['first_name', 'last_name', 'password' ]
        
class ProfileUpdatePhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['photo', 'photo_user']
              
class ProfileUpdateSerializer(serializers.ModelSerializer):
    user = UserUpdateSerializer(required=False)
    class Meta:
        model = Profile
        fields = ['user', 'date_of_birth', 'myskils', 'links' ]
    def update(self, instance, validated_data):
        user_data = validated_data.pop('user')
        if user_data:
            auth_user = get_object_or_404(User, id=self.context['request'].user.id)
            user = UserUpdateSerializer(auth_user, user_data, partial=True)
            if user.is_valid():
                user.save()
        myskils = validated_data.pop('myskils')
        instance.myskils.set(myskils)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
    
class UserDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ['id', 'username', 'first_name', 'last_name',  ]
    
class ProfileDetailSerializer(serializers.ModelSerializer):
    user = UserDetailSerializer()
    photo = serializers.URLField(source='photo.name')
    myskils = serializers.SerializerMethodField('get_myskils')
    links = serializers.SerializerMethodField('get_links')
    def get_links(self, obj):
        return json.loads(obj.links)
    def get_myskils(self, obj):
        return obj.myskils.values()
    class Meta:
        model = Profile
        fields = ['id', 'user', 'date_of_birth', 'photo_user', \
                'photo', 'myskils', 'links' ]