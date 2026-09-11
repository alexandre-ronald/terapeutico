# Generated for CCS-002.
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("centrocirurgico", "0012_tipos_motivos_suspensao"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SuspensaoCirurgia",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("observacao", models.TextField(blank=True)),
                ("registrado_em", models.DateTimeField(auto_now_add=True)),
                (
                    "cirurgia",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="suspensao",
                        to="centrocirurgico.cirurgia",
                    ),
                ),
                (
                    "motivo",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="suspensoes",
                        to="centrocirurgico.motivosuspensao",
                    ),
                ),
                (
                    "registrado_por",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="suspensoes_cirurgicas_registradas",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "tipo",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="suspensoes",
                        to="centrocirurgico.tiposuspensao",
                    ),
                ),
            ],
            options={
                "verbose_name": "Suspensão de cirurgia",
                "verbose_name_plural": "Suspensões de cirurgia",
                "ordering": ("-registrado_em",),
            },
        ),
    ]
