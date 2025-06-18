from django.contrib import admin
from .models import Pokemon, UserStorage, StorageBox

admin.site.register(Pokemon)
admin.site.register(UserStorage)
admin.site.register(StorageBox)
