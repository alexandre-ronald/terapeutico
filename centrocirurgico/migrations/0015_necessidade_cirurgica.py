from django.db import migrations, models
from django.db.models.functions import Lower


class Migration(migrations.Migration):
    dependencies = [("centrocirurgico", "0014_auditoria_edicao_suspensao")]
    operations = [
        migrations.CreateModel(
            name="NecessidadeCirurgica",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=150)),
                ("descricao", models.TextField(blank=True)),
                ("dica_complemento", models.CharField(blank=True, help_text="Exemplo do complemento esperado: P1, Plaquetas ou Sangue O+.", max_length=200)),
                ("complemento_obrigatorio", models.BooleanField(default=False)),
                ("ativo", models.BooleanField(default=True)),
                ("ordem", models.PositiveIntegerField(default=0)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
            ],
            options={"verbose_name": "Necessidade cirúrgica", "verbose_name_plural": "Necessidades cirúrgicas", "ordering": ("ordem", "nome")},
        ),
        migrations.AddConstraint(model_name="necessidadecirurgica", constraint=models.UniqueConstraint(Lower("nome"), name="centrocirurgico_necessidade_nome_ci_uniq")),
    ]
