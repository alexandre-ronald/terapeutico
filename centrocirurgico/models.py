from django.db import models
from django.db.models import F
from django.db.models.functions import Lower
from datetime import date
from django.conf import settings
from django.core.exceptions import ValidationError

# Create your models here.
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
        return f"{self.procedimento} - {self.paciente.nome}"

class GiroSala(models.Model):
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE)
    cirurgia = models.ForeignKey(Cirurgia, on_delete=models.CASCADE)
    dataInicioCirurgia = models.DateTimeField(null=True)
    dataFinalCirurgia = models.DateTimeField(null=True)
    dataSaidaSala = models.DateTimeField(null=True)
    dataInicioDesmontagemSala = models.DateTimeField(null=True)
    dataFinalDesmontagemSala = models.DateTimeField(null=True)
    dataInicioLimpeza = models.DateTimeField(null=True)
    dataFinalLimpeza = models.DateTimeField(null=True)
    dataSalaLiberada = models.DateTimeField(null=True)
    observacao = models.TextField(default="", null=True)
    tipoLimpeza = models.CharField(max_length=1, blank=True, null=True)

    def __str__(self):
        return str(self.paciente)


class TipoSuspensao(models.Model):
    nome = models.CharField(max_length=150)
    descricao = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)
    ordem = models.PositiveIntegerField(default=0)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("ordem", "nome")
        verbose_name = "Tipo de suspensão"
        verbose_name_plural = "Tipos de suspensão"
        constraints = [
            models.UniqueConstraint(
                Lower("nome"),
                name="centrocirurgico_tipo_suspensao_nome_ci_uniq",
            ),
        ]

    def clean(self):
        super().clean()
        self.nome = (self.nome or "").strip()
        if not self.nome:
            raise ValidationError({"nome": "Informe o nome do tipo de suspensão."})

    def __str__(self):
        return self.nome


class MotivoSuspensao(models.Model):
    tipo = models.ForeignKey(
        TipoSuspensao,
        on_delete=models.PROTECT,
        related_name="motivos",
    )
    nome = models.CharField(max_length=200)
    descricao = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)
    ordem = models.PositiveIntegerField(default=0)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("ordem", "nome")
        verbose_name = "Motivo de suspensão"
        verbose_name_plural = "Motivos de suspensão"
        constraints = [
            models.UniqueConstraint(
                F("tipo"),
                Lower("nome"),
                name="centrocirurgico_motivo_tipo_nome_ci_uniq",
            ),
        ]

    def clean(self):
        super().clean()
        self.nome = (self.nome or "").strip()
        if not self.nome:
            raise ValidationError({"nome": "Informe o nome do motivo de suspensão."})
        if self.ativo and self.tipo_id and not self.tipo.ativo:
            raise ValidationError(
                {"ativo": "Não é possível ativar um motivo de um tipo inativo."}
            )

    def __str__(self):
        return f"{self.tipo} - {self.nome}"


class LimpezaTerminal(models.Model):
    CENTRO_CIRURGICO_CHOICES = [
        ('CCA', 'Centro Cirúrgico Adulto'),
        ('CCI', 'Centro Cirúrgico Infantil'),
        ('CCOF', 'Centro Cirúrgico Oftalmológico'),
    ]

    data = models.DateField(verbose_name="Data da limpeza")
    centro_cirurgico = models.CharField(
        max_length=10,
        choices=CENTRO_CIRURGICO_CHOICES,
        verbose_name="Centro Cirúrgico"
    )
    sala = models.CharField(max_length=10, verbose_name="Sala")

    inicio_enfermagem = models.DateTimeField(null=True, blank=True, verbose_name="Início Enfermagem")
    fim_enfermagem = models.DateTimeField(null=True, blank=True, verbose_name="Fim Enfermagem")
    usuario_inicio_enfermagem = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='inicio_limpezas_enfermagem'
    )
    usuario_fim_enfermagem = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='fim_limpezas_enfermagem'
    )
    inicio_higienizacao = models.DateTimeField(null=True, blank=True, verbose_name="Início Higienização")
    fim_higienizacao = models.DateTimeField(null=True, blank=True, verbose_name="Fim Higienização")
    usuario_inicio_higienizacao = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='inicio_limpezas_higienizacao'
    )
    usuario_fim_higienizacao = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='fim_limpezas_higienizacao'
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='limpezas_criadas',
        verbose_name="Registrado por"
    )

    class Meta:
        ordering = ['-data', '-criado_em']
        verbose_name = "Limpeza Terminal"
        verbose_name_plural = "Limpezas Terminais"
        unique_together = ('data', 'centro_cirurgico', 'sala')

    def __str__(self):
        return f"{self.centro_cirurgico} - {self.sala} - {self.data}"

    def clean(self):
        salas_validas = {
            'CCA': [f'SALA {i:02d}' for i in range(1, 10)] + ['RPA'],
            'CCI': [f'SALA {i:02d}' for i in range(1, 4)] + ['RPA'],
            'CCOF': [f'SALA {i:02d}' for i in range(1, 4)] + ['RPA'],
        }
        if self.centro_cirurgico and self.sala:
            if self.sala not in salas_validas.get(self.centro_cirurgico, []):
                raise ValidationError({'sala': 'Sala inválida para o centro selecionado.'})
