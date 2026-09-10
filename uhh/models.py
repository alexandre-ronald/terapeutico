from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


# =========================
# PACIENTE
# =========================
class Paciente(models.Model):

    nome = models.CharField(max_length=200)

    prontuario = models.CharField(max_length=50, unique=True)

    grupo_sanguineo = models.CharField(max_length=3)
    fator_rh = models.CharField(max_length=1)

    def __str__(self):
        return f"{self.prontuario} - {self.nome}"

    @property
    def grupo_completo(self):
        return f"{self.grupo_sanguineo}{self.fator_rh}"


# =========================
# SOLICITAÇÃO
# =========================
class SolicitacaoHemocomponente(models.Model):

    STATUS = [
        ('aberta', 'Aberta'),
        ('atendida_parcial', 'Atendida Parcialmente'),
        ('atendida_total', 'Atendida Totalmente'),
        ('cancelada', 'Cancelada'),
    ]

    data_solicitacao = models.DateTimeField(auto_now_add=True)

    solicitante = models.CharField(max_length=200)
    unidade = models.CharField(max_length=200, blank=True, null=True)

    observacoes = models.TextField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default='aberta'
    )

    def __str__(self):
        return f"Solicitação #{self.id} - {self.solicitante}"


# =========================
# ITEM DA SOLICITAÇÃO
# =========================
class ItemSolicitacaoHemocomponente(models.Model):

    HEMOCOMPONENTES = [
        ('CH', 'Concentrado de Hemácias'),
        ('CHFILTRADO', 'Concentrado de Hemácias Filtrado'),
        ('FRACAOCH', 'Fração de Concentrado de Hemácias'),
        ('PLASMA', 'Plasma Fresco Congelado'),
        ('PLAQUETAS', 'Concentrado de Plaquetas'),
        ('CRIO', 'Crioprecipitado'),
    ]

    solicitacao = models.ForeignKey(
        SolicitacaoHemocomponente,
        on_delete=models.CASCADE,
        related_name="itens"
    )

    hemocomponente = models.CharField(
        max_length=20,
        choices=HEMOCOMPONENTES
    )

    grupo_sanguineo = models.CharField(max_length=3, blank=True)
    fator_rh = models.CharField(max_length=1, blank=True)

    ml = models.PositiveIntegerField(null=True, blank=True)

    quantidade = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.hemocomponente} - {self.quantidade}"


# =========================
# RECEBIMENTO
# =========================
class RecebimentoHemocomponente(models.Model):

    solicitacao = models.ForeignKey(
        SolicitacaoHemocomponente,
        on_delete=models.CASCADE,
        related_name="recebimentos"
    )

    data_recebimento = models.DateTimeField(auto_now_add=True)

    recebido_por = models.CharField(max_length=200)

    observacoes = models.TextField(blank=True)

    def __str__(self):
        return f"Recebimento #{self.id} - Solicitação {self.solicitacao.id}"


# =========================
# BOLSA DE SANGUE
# =========================
class BolsaSangue(models.Model):

    STATUS = [
        ('estoque', 'Em estoque'),
        ('reservada', 'Reservada'),
        ('liberada', 'Liberada'),
        ('transfundida', 'Transfundida'),
        ('devolvida', 'Devolvida'),
        ('descartada', 'Descartada'),
    ]

    numero_bolsa = models.CharField(max_length=50, unique=True)
    numero_macarrao = models.CharField(max_length=50, unique=True)

    hemocomponente = models.CharField(max_length=50)

    grupo_sanguineo = models.CharField(max_length=3)
    fator_rh = models.CharField(max_length=1)

    volume_ml = models.PositiveIntegerField(
        verbose_name="Volume (ml)",
        help_text="Ex: 250, 300, 450",
        default=0
    )

    data_coleta = models.DateField()
    data_validade = models.DateField()

    recebimento = models.ForeignKey(
        RecebimentoHemocomponente,
        on_delete=models.CASCADE,
        related_name="bolsas"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default='estoque'
    )

    data_criacao = models.DateTimeField(auto_now_add=True)
    #data_criacao = models.DateTimeField(null=True, blank=True)

    observacoes = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['grupo_sanguineo', 'fator_rh']),
        ]

    def __str__(self):
        return f"{self.numero_bolsa} | Mac: {self.numero_macarrao}"

    def clean(self):
        if self.data_validade <= self.data_coleta:
            raise ValidationError("Data de validade deve ser maior que a data de coleta")

    @property
    def grupo_completo(self):
        return f"{self.grupo_sanguineo}{self.fator_rh}"

    @property
    def esta_vencida(self):
        return self.data_validade < timezone.now().date()


# =========================
# RETORNO (UNIFICADO)
# =========================
class RetornoSolicitacao(models.Model):

    item_solicitacao = models.ForeignKey(
        ItemSolicitacaoHemocomponente,
        on_delete=models.CASCADE,
        related_name="retornos"
    )

    bolsa = models.ForeignKey(
        BolsaSangue,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    recebido = models.BooleanField(default=False)

    data_registro = models.DateTimeField(auto_now_add=True)

    observacoes = models.TextField(blank=True)

    def __str__(self):
        return f"Retorno Item {self.item_solicitacao.id}"


# =========================
# PROVA CRUZADA
# =========================
class ProvaCruzada(models.Model):

    RESULTADO = [
        ('compativel', 'Compatível'),
        ('incompativel', 'Incompatível'),
    ]

    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.CASCADE,
        related_name="provas"
    )

    bolsa = models.ForeignKey(
        BolsaSangue,
        on_delete=models.CASCADE,
        related_name="provas"
    )

    data_prova = models.DateTimeField(auto_now_add=True)

    resultado = models.CharField(
        max_length=20,
        choices=RESULTADO
    )

    realizado_por = models.CharField(max_length=200)

    observacoes = models.TextField(blank=True)

    def clean(self):
        if self.bolsa.esta_vencida:
            raise ValidationError("Não é possível realizar prova cruzada com bolsa vencida")

    def __str__(self):
        return f"Prova Cruzada - {self.paciente}"


# =========================
# LIBERAÇÃO
# =========================
class LiberacaoBolsa(models.Model):

    prova_cruzada = models.OneToOneField(
        ProvaCruzada,
        on_delete=models.CASCADE,
        related_name="liberacao"
    )

    data_liberacao = models.DateTimeField(auto_now_add=True)

    liberado_por = models.CharField(max_length=200)

    setor_destino = models.CharField(max_length=200)

    observacoes = models.TextField(blank=True)

    def __str__(self):
        return f"Liberação - Bolsa {self.prova_cruzada.bolsa.numero_bolsa}"


# =========================
# DEVOLUÇÃO
# =========================
class DevolucaoBolsa(models.Model):

    STATUS = [
        ('aprovada', 'Aprovada para Reintegração'),
        ('descartada', 'Descartada'),
    ]

    bolsa = models.ForeignKey(
        BolsaSangue,
        on_delete=models.CASCADE,
        related_name="devolucoes"
    )

    liberacao = models.ForeignKey(
        LiberacaoBolsa,
        on_delete=models.CASCADE,
        related_name="devolucoes"
    )

    data_devolucao = models.DateTimeField(auto_now_add=True)

    devolvido_por = models.CharField(max_length=200)

    setor_origem = models.CharField(max_length=200)

    condicao_bolsa = models.CharField(
        max_length=200,
        help_text="Ex: refrigerada, temperatura ambiente, violação de lacre"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS
    )

    observacoes = models.TextField(blank=True)

    def __str__(self):
        return f"Devolução - Bolsa {self.bolsa.numero_bolsa}"