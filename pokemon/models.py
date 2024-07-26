from evennia import DefaultCharacter
from django.db import models

class Pokemon(models.Model):
    name = models.CharField(max_length=255)
    level = models.IntegerField()
    type_ = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.id}: {self.name} (Level {self.level}, Type: {self.type_})"

class UserStorage(models.Model):
    user = models.OneToOneField(DefaultCharacter, on_delete=models.CASCADE)
    active_pokemon = models.ManyToManyField(Pokemon, related_name='active_users')
    stored_pokemon = models.ManyToManyField(Pokemon, related_name='stored_users')
