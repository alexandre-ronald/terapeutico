from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("centrocirurgico", "0019_programacao_leito_paciente"),
    ]

    operations = [
        migrations.AddField(
            model_name="girosala",
            name="dataInicioAnestesia",
            field=models.DateTimeField(null=True),
        ),
        migrations.AddField(
            model_name="programacaocirurgia",
            name="tipo_cirurgia",
            field=models.CharField(
                choices=[("eletiva", "Eletiva"), ("extra_mapa", "Extra Mapa")],
                default="",
                max_length=20,
            ),
            preserve_default=False,
        ),
    ]
