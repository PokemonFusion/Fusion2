from django.contrib import admin
from .models import Pokemon, UserStorage, Trainer, GymBadge

admin.site.register(Pokemon)
admin.site.register(UserStorage)
admin.site.register(Trainer)
admin.site.register(GymBadge)
