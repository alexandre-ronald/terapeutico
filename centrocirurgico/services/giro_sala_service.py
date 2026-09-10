from django.db.models import (
    Avg,
    Count,
    DurationField,
    ExpressionWrapper,
    F,
    FloatField,
)
from django.db.models.functions import Extract


class GiroSalaService:

    META = 30

    @classmethod
    def calcular(cls, queryset):

        queryset = (
            queryset
            .annotate(
                tempo_giro=ExpressionWrapper(
                    F("dataSalaLiberada") - F("dataSaidaSala"),
                    output_field=DurationField(),
                )
            )
            .annotate(
                minutos=Extract(
                    "tempo_giro",
                    "epoch",
                    output_field=FloatField()
                ) / 60
            )
        )

        total = queryset.count()

        if total == 0:
            return cls.contexto_vazio()

        media = queryset.aggregate(
            media=Avg("minutos")
        )["media"] or 0

        melhor = queryset.order_by("minutos").first()
        pior = queryset.order_by("-minutos").first()

        salas = list(
            queryset
            .values("cirurgia__sala")
            .annotate(
                quantidade=Count("id"),
                media=Avg("minutos")
            )
            .order_by("-media")
        )

        #####################################################
        # Classificação das salas
        #####################################################

        for sala in salas:

            status, badge = cls.classificar(sala["media"])

            sala["status"] = status
            sala["badge"] = badge

        #####################################################

        status, badge = cls.classificar(media)

        percentual = round((media / cls.META) * 100, 1)

        return {

            "media": round(media,1),

            "meta": cls.META,

            "percentual_meta": percentual,

            "total": total,

            "melhor": round(melhor.minutos,1),

            "pior": round(pior.minutos,1),

            "status": status,

            "badge": badge,

            "salas": salas

        }

    ########################################################

    @classmethod
    def classificar(cls, valor):

        if valor <= 20:
            return "Excelente", "success"

        elif valor <= 30:
            return "Bom", "warning"


        return "Crítico", "danger"

    ########################################################

    @classmethod
    def contexto_vazio(cls):

        return {

            "media":0,

            "meta":cls.META,

            "percentual_meta":0,

            "total":0,

            "melhor":0,

            "pior":0,

            "status":"Sem dados",

            "badge":"secondary",

            "salas":[]
        }