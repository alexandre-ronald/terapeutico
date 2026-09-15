from django import forms
from .models import ProgramacaoCirurgia


class ProgramacaoCirurgiaForm(forms.ModelForm):
    class Meta:
        model = ProgramacaoCirurgia
        fields = (
            "tipo_cirurgia", "sala_painel", "hora_painel", "anestesistas", "instrumentador",
            "circulante", "residente", "enfermeiro", "outros_profissionais", "observacao",
        )
        widgets = {
            "hora_painel": forms.TimeInput(format="%H:%M", attrs={"type": "time"}),
            "anestesistas": forms.Textarea(attrs={"rows": 2, "placeholder": "Um nome por linha"}),
            "outros_profissionais": forms.Textarea(attrs={"rows": 2, "placeholder": "Um nome por linha"}),
            "observacao": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
        self.fields["tipo_cirurgia"].widget.attrs["class"] = "form-select"
        self.fields["tipo_cirurgia"].choices = (("", "Selecione o tipo"),) + ProgramacaoCirurgia.TIPOS_CIRURGIA
        self.fields["sala_painel"].widget.attrs["class"] = "form-select"
        self.fields["sala_painel"].choices = (("", "Selecione a sala"),) + ProgramacaoCirurgia.SALAS

    def clean_sala_painel(self):
        sala = (self.cleaned_data.get("sala_painel") or "").strip()
        if not sala:
            raise forms.ValidationError("Informe a sala que será exibida no painel.")
        return sala
