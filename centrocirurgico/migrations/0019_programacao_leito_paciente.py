from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("centrocirurgico", "0018_programacao_sala_1_a_9")]
    operations = [
        migrations.AddField(
            model_name="programacaocirurgia",
            name="leito_paciente",
            field=models.CharField(blank=True, max_length=50),
        ),
    ]
