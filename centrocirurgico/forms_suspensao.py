from django import forms

from .models import MotivoSuspensao, SuspensaoCirurgia, TipoSuspensao


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



class SuspensaoCirurgiaForm(BootstrapModelForm):
    class Meta:
        model = SuspensaoCirurgia
        fields = ("tipo", "motivo", "observacao")
        widgets = {
            "observacao": forms.Textarea(
                attrs={
                    "rows": 4,
                    "maxlength": 2000,
                    "placeholder": "Descreva alguma informação adicional, se necessário.",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tipo"].queryset = TipoSuspensao.objects.filter(ativo=True)
        self.fields["tipo"].widget.attrs["class"] = "form-select"
        self.fields["motivo"].widget.attrs["class"] = "form-select"

        tipo_id = None
        if self.is_bound:
            tipo_id = self.data.get(self.add_prefix("tipo"))
        elif self.instance.pk:
            tipo_id = self.instance.tipo_id
        elif self.initial.get("tipo"):
            tipo = self.initial["tipo"]
            tipo_id = getattr(tipo, "pk", tipo)

        self.fields["motivo"].queryset = MotivoSuspensao.objects.none()
        if tipo_id:
            self.fields["motivo"].queryset = MotivoSuspensao.objects.filter(
                tipo_id=tipo_id,
                tipo__ativo=True,
                ativo=True,
            )

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get("tipo")
        motivo = cleaned_data.get("motivo")

        if tipo and not tipo.ativo:
            self.add_error("tipo", "Selecione um tipo ativo.")
        if motivo:
            if not motivo.ativo:
                self.add_error("motivo", "Selecione um motivo ativo.")
            elif tipo and motivo.tipo_id != tipo.id:
                self.add_error(
                    "motivo",
                    "O motivo selecionado não pertence ao tipo informado.",
                )
        return cleaned_data
