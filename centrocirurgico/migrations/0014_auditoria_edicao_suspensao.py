# Generated for CCS-003.
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("centrocirurgico", "0013_suspensao_cirurgia"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="suspensaocirurgia",
            name="atualizado_em",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="suspensaocirurgia",
            name="atualizado_por",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="suspensoes_cirurgicas_atualizadas",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
