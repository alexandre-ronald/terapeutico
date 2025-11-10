from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models

class User(AbstractUser):
    # Campos adicionais ao modelo de usuário
    choices_perfil = ( ('administrador', 'Administrador'),
                       ('gestor', 'Gestor'))
    
    perfil_acesso = models.CharField(max_length=30, choices = choices_perfil,default='administrador',
        help_text="Tipo de perfil de acesso do usuário")
   
    matricula = models.CharField(max_length=100, null=True, help_text="Número de matrícula do usuário")
    ativo = models.BooleanField(default=True, help_text="Indica se o usuário está ativo no sistema")
    foto_perfil = models.ImageField(upload_to='perfil_fotos/', blank=True, null=True, help_text="Imagem de perfil do usuário")
   
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.matricula})"

