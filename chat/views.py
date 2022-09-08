from django.shortcuts import render
from rest_framework.views import APIView
from django.contrib.auth import authenticate, login
from rest_framework.response import Response
from rest_framework import status
from chat.models import Room
import uuid
from django.contrib.auth.models import User
