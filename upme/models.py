# Create your models here.
from django.db import models
from datetime import date
from django.conf import settings

class Material(models.Model):
    nome = models.CharField(max_length=200, blank=True, null=True) 
    def __str__(self):
        return self.nome

class Especialidade(models.Model):
    nome = models.CharField(max_length=200, blank=True, null=True) 
    def __str__(self):
        return self.nome

class Procedimento(models.Model):
    especialidade = models.ForeignKey(Especialidade, on_delete=models.CASCADE, null=True)
    nome = models.CharField(max_length=200, blank=True, null=True) 
    def __str__(self):
        return self.nome

class Kit(models.Model):
    nome = models.CharField(max_length=200, blank=True, null=True) 
    especialidade = models.ForeignKey(Especialidade, on_delete=models.CASCADE, null=True)
    def __str__(self):
        return f"Kit: {self.nome}"

class Kit_Material(models.Model):
    kit = models.ForeignKey(Kit, on_delete=models.CASCADE, null=True)
    material = models.ForeignKey(Material, on_delete=models.CASCADE, null=True)
    quantidade = models.IntegerField(default=1)


class Paciente(models.Model):
    nome = models.CharField(max_length=200)
    nascimento = models.DateField(null=True, blank=True)
    prontuario = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return self.nome

class Cirurgia(models.Model):
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE)
    especialidade = models.CharField(max_length=200, blank=True, null=True)
    procedimento = models.CharField(max_length=200, blank=True, null=True)
    medico = models.CharField(max_length=200, blank=True, null=True)
    sala = models.CharField(max_length=50, blank=True, null=True)
    data = models.DateField(default=date.today)
    hora = models.TimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.procedimento.nome} - {self.paciente.nome}"

class CirurgiaMaterial(models.Model):
    cirurgia = models.ForeignKey(Cirurgia, on_delete=models.CASCADE, null=True)
    material = models.ForeignKey(Material, on_delete=models.CASCADE, null=True)
    kit_material = models.ForeignKey(Kit_Material, on_delete=models.CASCADE, null=True)
    quantidade_solicitada = models.IntegerField(default=1)
    quantidade_fornecida = models.IntegerField(default=0)
    quantidade_devolvida = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.material.nome} ({self.quantidade_fornecida}/{self.quantidade_solicitada})"
