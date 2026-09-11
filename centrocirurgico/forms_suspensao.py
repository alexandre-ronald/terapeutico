from django import forms

from .models import MotivoSuspensao, TipoSuspensao


class BootstrapModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault("class", "form-check-input")
            else:
                field.widget.attrs.setdefault("class", "form-control")


class TipoSuspensaoForm(BootstrapModelForm):
    class Meta:
        model = TipoSuspensao
        fields = ("nome", "descricao", "ordem", "ativo")
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 3}),
            "ordem": forms.NumberInput(attrs={"min": 0}),
        }

    def clean_nome(self):
        nome = (self.cleaned_data.get("nome") or "").strip()
        if not nome:
            raise forms.ValidationError("Informe o nome do tipo de suspensão.")
        return nome


class MotivoSuspensaoForm(BootstrapModelForm):
    class Meta:
        model = MotivoSuspensao
        fields = ("tipo", "nome", "descricao", "ordem", "ativo")
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 3}),
            "ordem": forms.NumberInput(attrs={"min": 0}),
        }

    def clean_nome(self):
        nome = (self.cleaned_data.get("nome") or "").strip()
        if not nome:
            raise forms.ValidationError("Informe o nome do motivo de suspensão.")
        return nome

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get("tipo")
        if cleaned_data.get("ativo") and tipo and not tipo.ativo:
            self.add_error(
                "ativo",
                "Não é possível ativar um motivo de um tipo inativo.",
            )
        return cleaned_data
