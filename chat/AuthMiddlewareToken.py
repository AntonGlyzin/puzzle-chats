from channels.db import database_sync_to_async
from django.http import QueryDict
from base.models import Profile
from rest_framework_simplejwt.authentication import JWTAuthentication

@database_sync_to_async
def get_user(raw_token, ip):
    try:
        jwt = JWTAuthentication()
        valid_token = jwt.get_validated_token(raw_token)
        user = jwt.get_user(valid_token)
        user = Profile.objects.get(user__id=user.id, user__is_active=True)
        if not ip in user.my_ip['ip']:
            return None
        return user.user
    except BaseException as err:
        return None

class AuthMiddlewareToken:
    def __init__(self, app):
        self.app = app
    async def __call__(self, scope, receive, send):
        dict_headers = dict(scope['headers'])
        ip = dict_headers.get('x-forwarded-for') or scope['client'][0]
        user_data = QueryDict(scope['query_string'])
        scope['user'] = await get_user(user_data.get('token', None), ip)
        return await self.app(scope, receive, send)
            