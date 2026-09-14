import re

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
    dataInicioAnestesia = models.DateTimeField(null=True)
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


class SuspensaoCirurgia(models.Model):
    cirurgia = models.OneToOneField(
        Cirurgia,
        on_delete=models.PROTECT,
        related_name="suspensao",
    )
    tipo = models.ForeignKey(
        TipoSuspensao,
        on_delete=models.PROTECT,
        related_name="suspensoes",
    )
    motivo = models.ForeignKey(
        MotivoSuspensao,
        on_delete=models.PROTECT,
        related_name="suspensoes",
    )
    observacao = models.TextField(blank=True)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="suspensoes_cirurgicas_registradas",
    )
    registrado_em = models.DateTimeField(auto_now_add=True)
    atualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="suspensoes_cirurgicas_atualizadas",
    )
    atualizado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-registrado_em",)
        verbose_name = "Suspensão de cirurgia"
        verbose_name_plural = "Suspensões de cirurgia"

    def clean(self):
        super().clean()
        if self.tipo_id and self.motivo_id and self.motivo.tipo_id != self.tipo_id:
            raise ValidationError(
                {"motivo": "O motivo selecionado não pertence ao tipo informado."}
            )

    def __str__(self):
        return f"{self.cirurgia} - {self.motivo.nome}"


class NecessidadeCirurgica(models.Model):
    nome = models.CharField(max_length=150)
    descricao = models.TextField(blank=True)
    dica_complemento = models.CharField(
        max_length=200,
        blank=True,
        help_text="Exemplo do complemento esperado: P1, Plaquetas ou Sangue O+.",
    )
    complemento_obrigatorio = models.BooleanField(default=False)
    ativo = models.BooleanField(default=True)
    ordem = models.PositiveIntegerField(default=0)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("ordem", "nome")
        verbose_name = "Necessidade cirúrgica"
        verbose_name_plural = "Necessidades cirúrgicas"
        constraints = [
            models.UniqueConstraint(
                Lower("nome"),
                name="centrocirurgico_necessidade_nome_ci_uniq",
            ),
        ]

    def clean(self):
        super().clean()
        self.nome = (self.nome or "").strip()
        self.descricao = (self.descricao or "").strip()
        self.dica_complemento = (self.dica_complemento or "").strip()
        if not self.nome:
            raise ValidationError({"nome": "Informe o nome da necessidade."})

    def __str__(self):
        return self.nome


class ProgramacaoCirurgia(models.Model):
    SALAS = tuple((str(numero), f"Sala {numero}") for numero in range(1, 10))
    ELETIVA = "eletiva"
    EXTRA_MAPA = "extra_mapa"
    TIPOS_CIRURGIA = (
        (ELETIVA, "Eletiva"),
        (EXTRA_MAPA, "Extra Mapa"),
    )
    RASCUNHO = "rascunho"
    ENVIADA = "enviada"
    FINALIZADA = "finalizada"
    STATUS_CHOICES = (
        (RASCUNHO, "Rascunho"),
        (ENVIADA, "Enviada ao painel"),
        (FINALIZADA, "Finalizada"),
    )

    cirurgia = models.OneToOneField(Cirurgia, on_delete=models.PROTECT, related_name="programacao")
    sala_painel = models.CharField(max_length=2, choices=SALAS)
    hora_painel = models.TimeField(null=True, blank=True)
    leito_paciente = models.CharField(max_length=50, blank=True)
    tipo_cirurgia = models.CharField(max_length=20, choices=TIPOS_CIRURGIA)
    anestesistas = models.TextField(blank=True)
    instrumentador = models.CharField(max_length=250, blank=True)
    circulante = models.CharField(max_length=250, blank=True)
    residente = models.CharField(max_length=250, blank=True)
    enfermeiro = models.CharField(max_length=250, blank=True)
    outros_profissionais = models.TextField(blank=True)
    observacao = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=RASCUNHO)
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="programacoes_criadas")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="programacoes_atualizadas")
    atualizado_em = models.DateTimeField(auto_now=True)
    enviado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("cirurgia__data", "cirurgia__hora", "cirurgia__sala")
        verbose_name = "Programação de cirurgia"
        verbose_name_plural = "Programações de cirurgia"

    def __str__(self):
        return f"{self.cirurgia} — {self.get_status_display()}"

    def save(self, *args, **kwargs):
        if not self.sala_painel and self.cirurgia_id:
            sala_original = self.cirurgia.sala or ""
            numeros = re.findall(r"(?<!\\d)([1-9])(?!\\d)", sala_original)
            self.sala_painel = numeros[-1] if numeros else ""
        if self.hora_painel is None and self.cirurgia_id:
            self.hora_painel = self.cirurgia.hora
        super().save(*args, **kwargs)


class ProgramacaoNecessidade(models.Model):
    programacao = models.ForeignKey(ProgramacaoCirurgia, on_delete=models.CASCADE, related_name="necessidades")
    necessidade = models.ForeignKey(NecessidadeCirurgica, on_delete=models.PROTECT, related_name="programacoes")
    complemento = models.CharField(max_length=250, blank=True)
    atendida = models.BooleanField(default=False)
    atendida_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="necessidades_cirurgicas_atendidas")
    atendida_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("necessidade__ordem", "necessidade__nome")
        constraints = [models.UniqueConstraint(fields=("programacao", "necessidade"), name="centrocirurgico_programacao_necessidade_uniq")]
        verbose_name = "Necessidade da programação"
        verbose_name_plural = "Necessidades da programação"

    def clean(self):
        super().clean()
        self.complemento = (self.complemento or "").strip()
        if self.necessidade_id and self.necessidade.complemento_obrigatorio and not self.complemento:
            raise ValidationError({"complemento": "Informe o complemento desta necessidade."})

    def __str__(self):
        return f"{self.programacao} — {self.necessidade}"


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
