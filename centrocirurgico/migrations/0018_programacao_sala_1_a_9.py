import re
from django.db import migrations, models


def normalizar_salas(apps, schema_editor):
    Programacao = apps.get_model("centrocirurgico", "ProgramacaoCirurgia")
    for programacao in Programacao.objects.all():
        encontrados = re.findall(r"(?<!\\d)([1-9])(?!\\d)", programacao.sala_painel or "")
        programacao.sala_painel = encontrados[-1] if encontrados else ""
        programacao.save(update_fields=("sala_painel",))


class Migration(migrations.Migration):
    dependencies = [("centrocirurgico", "0017_programacao_sala_hora_e_equipe")]
    operations = [
        migrations.RunPython(normalizar_salas, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="programacaocirurgia",
            name="sala_painel",
            field=models.CharField(
                choices=[("1", "Sala 1"), ("2", "Sala 2"), ("3", "Sala 3"),
                         ("4", "Sala 4"), ("5", "Sala 5"), ("6", "Sala 6"),
                         ("7", "Sala 7"), ("8", "Sala 8"), ("9", "Sala 9")],
                max_length=2,
            ),
        ),
    ]
