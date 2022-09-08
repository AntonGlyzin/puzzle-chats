from django.urls import path
from genie.views import entryGenie, sendMessage, checkHolidays

urlpatterns = [
    path('AAGhTISdT5GkVG1MtNdB2Uepd8irC9BJDFI/', entryGenie),
    path('send-message/', sendMessage),
    # path('uod0RBWFc4n3CWeuwGUYw/', checkHolidays)
]