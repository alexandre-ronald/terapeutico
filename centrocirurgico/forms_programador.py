from django import forms
from .models import ProgramacaoCirurgia


class ProgramacaoCirurgiaForm(forms.ModelForm):
    class Meta:
        model = ProgramacaoCirurgia
        fields = ("anestesistas", "instrumentador", "outros_profissionais", "observacao")
        widgets = {
            "anestesistas": forms.Textarea(attrs={"rows": 2, "placeholder": "Um nome por linha"}),
            "outros_profissionais": forms.Textarea(attrs={"rows": 2, "placeholder": "Um nome por linha"}),
            "observacao": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
