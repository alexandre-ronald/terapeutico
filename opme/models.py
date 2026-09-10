from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError

class Empresa(models.Model):
    nome = models.CharField(max_length=200)

    def __str__(self):
        return self.nome


class Produto(models.Model):
    descricao = models.CharField(max_length=200)
    referencia = models.CharField(max_length=100, blank=True, verbose_name="Referência")
    fabricante = models.CharField(max_length=100, blank=True)
    unidade = models.CharField(max_length=20, default="un", verbose_name="Unidade")

    def __str__(self):
        return f"{self.descricao} ({self.referencia or 'sem ref'})"


class Caixa(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT)
    identificador = models.CharField(max_length=200, unique=True, verbose_name="Identificador da caixa")
    descricao = models.CharField(max_length=200, blank=True)
    data_cadastro = models.DateField(default=timezone.now)

    def __str__(self):
        return f"{self.identificador} - {self.empresa}"


class CaixaItem(models.Model):
    """Composição PADRÃO da caixa (fixa para todos as consignação)"""
    caixa = models.ForeignKey(Caixa, on_delete=models.CASCADE, related_name="itens_padrao")
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT)
    quantidade_esperada = models.PositiveIntegerField(default=1, verbose_name="Qtde esperada")

    class Meta:
        unique_together = [['caixa', 'produto']]
        ordering = ['produto__descricao']
        verbose_name = "Item padrão da caixa"
        verbose_name_plural = "Itens padrão da caixa"

    def __str__(self):
        return f"{self.produto} × {self.quantidade_esperada} ({self.caixa})"


class Consignacao(models.Model):
    caixa = models.ForeignKey('Caixa', on_delete=models.PROTECT, verbose_name="Caixa / Kit")
    
    data_consignacao = models.DateTimeField(
        default=timezone.now,
        verbose_name="Data da consignação / recebimento no hospital"
    )
    
    data_devolucao = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Data efetiva da devolução"
    )
    
    status = models.CharField(
        max_length=20,
        default='CONSIGNADO',
        choices=[
            ('CONSIGNADO', 'Consignado (em uso no hospital)'),
            ('DEVOLVIDO', 'Devolvido (total)'),
            ('DEVOLVIDO_PARCIAL', 'Devolvido parcial'),
        ],
        verbose_name="Status da consignação"
    )
    
    observacao = models.TextField(
        blank=True,
        verbose_name="Observações gerais da consignação"
    )
    
    responsavel_entrega = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='consignacoes_entregues',
        verbose_name="Responsável pela entrega / consignação"
    )
    
    responsavel_devolucao = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='consignacoes_devolvidas',
        verbose_name="Responsável pela devolução / conferência"
    )

    observacao_devolucao = models.TextField(
        blank=True,
        null=True,
        verbose_name="Observações gerais da devolução"
    )

    def __str__(self):
        return f"Consignação #{self.id} - {self.caixa} ({self.data_consignacao.date()})"

    class Meta:
        verbose_name = "Consignação OPME"
        verbose_name_plural = "Consignações OPME"
        ordering = ['-data_consignacao']

    def get_total_esperado(self):
        """Total de itens esperados (composição padrão da caixa)"""
        return sum(
            item.quantidade_esperada 
            for item in self.caixa.itens_padrao.all()
        )

    def get_total_recebido(self):
        """Total de itens efetivamente recebidos (após conferência)"""
        return sum(
            (item.quantidade_recebida if item.quantidade_recebida is not None else item.caixa_item.quantidade_esperada)
            if not item.removido_na_chegada else 0
            for item in self.itens.all()
        )

    def get_total_devolvido(self):
        """Total de itens devolvidos"""
        return sum(item.quantidade_devolvida for item in self.itens.all())

    def get_total_consumido(self):
        """Total de itens consumidos / perdidos"""
        return sum(item.quantidade_consumida for item in self.itens.all())

    def get_percentual_devolucao(self):
        """Percentual de devolução (%)"""
        recebido = self.get_total_recebido()
        if recebido == 0:
            return 0.0
        return round((self.get_total_devolvido() / recebido) * 100, 1)

    def get_itens_consumidos(self):
        """
        Retorna lista de itens com diferenças ou consumo para relatório.
        Inclui TODOS os itens para relatórios completos.
        """
        itens = []
        for item in self.itens.all().select_related('caixa_item__produto'):
            qtd_esperada = item.caixa_item.quantidade_esperada
            qtd_reposta = item.quantidade_reposta if item.quantidade_reposta is not None else 0
            qtd_recebida = item.quantidade_recebida if item.quantidade_recebida is not None else 0
            qtd_devolvida = item.quantidade_devolvida
            consumido = max(0, qtd_recebida - qtd_devolvida)

            itens.append({
                'produto': item.caixa_item.produto,
                'esperado': qtd_esperada,
                'recebido': qtd_recebida,
                'devolvido': qtd_devolvida,
                'reposto': qtd_reposta,
                'consumido': consumido,
                'observacao': item.observacao or '',
                'removido_na_chegada': item.removido_na_chegada,
                'observacao_devolucao': item.observacao_devolucao or '',
            })
        return itens

    def save(self, *args, **kwargs):
        """
        Atualiza status automaticamente ao salvar (devolução completa/parcial).
        """
        if self.data_devolucao and self.status == 'CONSIGNADO':
            total_recebido = self.get_total_recebido()
            total_devolvido = self.get_total_devolvido()
            if total_devolvido >= total_recebido:
                self.status = 'DEVOLVIDO'
            else:
                self.status = 'DEVOLVIDO_PARCIAL'

        super().save(*args, **kwargs)


class ConsignacaoItem(models.Model):
    """Registro real de cada item na consignação específica"""
    consignacao = models.ForeignKey(Consignacao, on_delete=models.CASCADE, related_name="itens")
    caixa_item = models.ForeignKey(CaixaItem, on_delete=models.PROTECT)

    quantidade_recebida = models.PositiveIntegerField(
        null=True, 
        blank=True, 
        validators=[MinValueValidator(0)],
        verbose_name="Qtde real recebida na entrega"
    )
    quantidade_devolvida = models.PositiveIntegerField(
        default=0, 
        verbose_name="Qtde devolvida"
    )

    quantidade_reposta= models.PositiveIntegerField(
        default=0, 
        verbose_name="Qtde reposta"
    )
    
    removido_na_chegada = models.BooleanField(
        default=False, 
        verbose_name="Removido/negado na conferência de chegada"
    )
    observacao = models.TextField(blank=True, null=True)

    observacao_devolucao = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = [['consignacao', 'caixa_item']]
        verbose_name = "Item da consignação"
        verbose_name_plural = "Itens da consignação"

    @property
    def quantidade_consumida(self):
        if self.removido_na_chegada:
            return 0
        qtd_entregue = self.quantidade_recebida if self.quantidade_recebida is not None else self.caixa_item.quantidade_esperada
        return max(0, qtd_entregue - self.quantidade_devolvida)

    def __str__(self):
        return f"{self.caixa_item.produto} (Consignação {self.consignacao.id})"
    
class ConsignacaoFoto(models.Model):
    TIPO_FOTO = [
        ('CHEGADA', 'Foto de Chegada / Recebimento'),
        ('DEVOLUCAO', 'Foto de Devolução'),
    ]

    consignacao = models.ForeignKey(Consignacao, on_delete=models.CASCADE, related_name='fotos')
    tipo = models.CharField(max_length=10, choices=TIPO_FOTO, verbose_name="Etapa")
    imagem = models.ImageField(
        upload_to='consignacoes/fotos/%Y/%m/%d/',
        verbose_name="Imagem"
    )
    descricao = models.CharField(max_length=200, blank=True, verbose_name="Descrição / Observação")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fotos_uploaded'
    )

    class Meta:
        verbose_name = "Foto da Consignação"
        verbose_name_plural = "Fotos do Consignação"
        ordering = ['uploaded_at']

    def __str__(self):
        return f"Foto {self.tipo} - Consignação #{self.consignacao.id}"
    