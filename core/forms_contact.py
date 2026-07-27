from django import forms

from .models import ContactMessage, WorkshopReview


class ContactMessageForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ("subject", "message")
        widgets = {"message": forms.Textarea(attrs={"rows": 5})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        css = (
            "mt-2 w-full rounded-xl border border-slate-200 bg-white px-4 py-3 "
            "outline-none focus:border-teal-500 focus:ring-4 focus:ring-teal-500/10"
        )
        for field in self.fields.values():
            field.widget.attrs["class"] = css


class WorkshopReviewForm(forms.ModelForm):
    class Meta:
        model = WorkshopReview
        fields = ("rating", "comment")
        widgets = {"comment": forms.Textarea(attrs={"rows": 4})}
        labels = {
            "rating": "تقييمك للخدمة",
            "comment": "شاركنا تجربتك",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        css = (
            "mt-2 w-full rounded-2xl border border-[#ded4c1] bg-[#fffdf8] "
            "px-4 py-3 outline-none focus:border-[#ad8f50] "
            "focus:ring-4 focus:ring-[#d8c18d]/20"
        )
        for field in self.fields.values():
            field.widget.attrs["class"] = css
