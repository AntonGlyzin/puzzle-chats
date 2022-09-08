from firebase_admin import storage
from django.utils.crypto import get_random_string
import os

class FireBaseStorage:
    def __init__(self):
        pass
    @staticmethod
    def get_publick_link(source, dist):
        bucket = storage.bucket()
        blob = bucket.blob(dist)
        blob.upload_from_filename(source)
        blob.make_public()
        return blob.public_url
    
def change_name_file(instance, filename):
    extension = "." + filename.split('.')[-1]
    filename = get_random_string(length=32) + extension
    return filename