from django.urls import path, re_path
from .views import checkCaptcha, \
                    getProtect, registerUserBag,\
                    UpdateUserBag, UpdateUserPhotoBag, DetailUserBag

urlpatterns = [
    path('api/checkcaptcha/', checkCaptcha),
    path('api/getprotect/', getProtect),
    path('api/bag/registration/user', registerUserBag.as_view()),
    path('api/bag/update/user', UpdateUserBag.as_view()),
    path('api/bag/detail/user', DetailUserBag.as_view({'get':'retrieve'})),
    path('api/bag/update/userphoto', UpdateUserPhotoBag.as_view())
]