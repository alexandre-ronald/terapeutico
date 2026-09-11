from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("centrocirurgico", "0015_necessidade_cirurgica"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(name="ProgramacaoCirurgia", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("anestesistas", models.TextField(blank=True)), ("instrumentador", models.CharField(blank=True, max_length=250)),
            ("outros_profissionais", models.TextField(blank=True)), ("observacao", models.TextField(blank=True)),
            ("status", models.CharField(choices=[("rascunho", "Rascunho"), ("enviada", "Enviada ao painel"), ("finalizada", "Finalizada")], default="rascunho", max_length=20)),
            ("criado_em", models.DateTimeField(auto_now_add=True)), ("atualizado_em", models.DateTimeField(auto_now=True)), ("enviado_em", models.DateTimeField(blank=True, null=True)),
            ("cirurgia", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="programacao", to="centrocirurgico.cirurgia")),
            ("criado_por", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="programacoes_criadas", to=settings.AUTH_USER_MODEL)),
            ("atualizado_por", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="programacoes_atualizadas", to=settings.AUTH_USER_MODEL)),
        ], options={"verbose_name": "Programação de cirurgia", "verbose_name_plural": "Programações de cirurgia", "ordering": ("cirurgia__data", "cirurgia__hora", "cirurgia__sala")}),
        migrations.CreateModel(name="ProgramacaoNecessidade", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("complemento", models.CharField(blank=True, max_length=250)), ("atendida", models.BooleanField(default=False)), ("atendida_em", models.DateTimeField(blank=True, null=True)),
            ("atendida_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="necessidades_cirurgicas_atendidas", to=settings.AUTH_USER_MODEL)),
            ("necessidade", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="programacoes", to="centrocirurgico.necessidadecirurgica")),
            ("programacao", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="necessidades", to="centrocirurgico.programacaocirurgia")),
        ], options={"verbose_name": "Necessidade da programação", "verbose_name_plural": "Necessidades da programação", "ordering": ("necessidade__ordem", "necessidade__nome")}),
        migrations.AddConstraint(model_name="programacaonecessidade", constraint=models.UniqueConstraint(fields=("programacao", "necessidade"), name="centrocirurgico_programacao_necessidade_uniq")),
    ]
