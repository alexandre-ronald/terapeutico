from django.db import migrations, models


def preencher_sala_hora(apps, schema_editor):
    Programacao = apps.get_model("centrocirurgico", "ProgramacaoCirurgia")
    for programacao in Programacao.objects.select_related("cirurgia").all():
        programacao.sala_painel = programacao.cirurgia.sala or ""
        programacao.hora_painel = programacao.cirurgia.hora
        programacao.save(update_fields=("sala_painel", "hora_painel"))


class Migration(migrations.Migration):
    dependencies = [("centrocirurgico", "0016_programacao_cirurgia")]
    operations = [
        migrations.AddField(model_name="programacaocirurgia", name="sala_painel", field=models.CharField(blank=True, default="", max_length=50)),
        migrations.AddField(model_name="programacaocirurgia", name="hora_painel", field=models.TimeField(blank=True, null=True)),
        migrations.AddField(model_name="programacaocirurgia", name="circulante", field=models.CharField(blank=True, max_length=250)),
        migrations.AddField(model_name="programacaocirurgia", name="residente", field=models.CharField(blank=True, max_length=250)),
        migrations.AddField(model_name="programacaocirurgia", name="enfermeiro", field=models.CharField(blank=True, max_length=250)),
        migrations.RunPython(preencher_sala_hora, migrations.RunPython.noop),
        migrations.AlterField(model_name="programacaocirurgia", name="sala_painel", field=models.CharField(max_length=50)),
    ]
