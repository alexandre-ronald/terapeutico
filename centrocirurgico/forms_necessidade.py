from django import forms

from .models import NecessidadeCirurgica


class NecessidadeCirurgicaForm(forms.ModelForm):
    class Meta:
        model = NecessidadeCirurgica
        fields = (
            "nome",
            "descricao",
            "dica_complemento",
            "complemento_obrigatorio",
            "ordem",
            "ativo",
        )
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 3}),
            "ordem": forms.NumberInput(attrs={"min": 0}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault("class", "form-check-input")
            else:
                field.widget.attrs.setdefault("class", "form-control")

    def clean_nome(self):
        nome = (self.cleaned_data.get("nome") or "").strip()
        if not nome:
            raise forms.ValidationError("Informe o nome da necessidade.")
        return nome
