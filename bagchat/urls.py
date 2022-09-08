from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenVerifyView
from base.views import EntryPointByPass

urlpatterns = [
    path('adminus/', admin.site.urls),
    path('martor/', include('martor.urls')),
    path('api/captcha/', include('captcha.urls')),
    path('api/genie/', include('genie.urls')),
    path('api/bag/', include('portfolio.urls')),
    path('api/token/', EntryPointByPass.as_view(), name='token_obtain_pair'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='verify_true'),
    path('', include('base.urls')),
]
