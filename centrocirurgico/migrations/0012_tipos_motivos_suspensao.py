# Generated for CCS-001.
import django.db.models.deletion
from django.db import migrations, models
from django.db.models import F
from django.db.models.functions import Lower


class Migration(migrations.Migration):

    dependencies = [
        ("centrocirurgico", "0011_rename_tipolavagem_girosala_tipolimpeza"),
    ]

    operations = [
        migrations.CreateModel(
            name="TipoSuspensao",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=150)),
                ("descricao", models.TextField(blank=True)),
                ("ativo", models.BooleanField(default=True)),
                ("ordem", models.PositiveIntegerField(default=0)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Tipo de suspensão",
                "verbose_name_plural": "Tipos de suspensão",
                "ordering": ("ordem", "nome"),
            },
        ),
        migrations.CreateModel(
            name="MotivoSuspensao",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=200)),
                ("descricao", models.TextField(blank=True)),
                ("ativo", models.BooleanField(default=True)),
                ("ordem", models.PositiveIntegerField(default=0)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                ("tipo", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="motivos", to="centrocirurgico.tiposuspensao")),
            ],
            options={
                "verbose_name": "Motivo de suspensão",
                "verbose_name_plural": "Motivos de suspensão",
                "ordering": ("ordem", "nome"),
            },
        ),
        migrations.AddConstraint(
            model_name="tiposuspensao",
            constraint=models.UniqueConstraint(
                Lower("nome"),
                name="centrocirurgico_tipo_suspensao_nome_ci_uniq",
            ),
        ),
        migrations.AddConstraint(
            model_name="motivosuspensao",
            constraint=models.UniqueConstraint(
                F("tipo"),
                Lower("nome"),
                name="centrocirurgico_motivo_tipo_nome_ci_uniq",
            ),
        ),
    ]
