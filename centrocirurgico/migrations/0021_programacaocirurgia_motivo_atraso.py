from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("centrocirurgico", "0020_tipo_cirurgia_inicio_anestesia"),
    ]

    operations = [
        migrations.AddField(
            model_name="programacaocirurgia",
            name="motivo_atraso",
            field=models.TextField(blank=True, verbose_name="Motivo do atraso"),
        ),
    ]
