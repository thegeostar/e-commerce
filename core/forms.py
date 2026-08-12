from django import forms
from core.models import CartOrder, ProductReview


class ProductReviewForm(forms.ModelForm):
    review = forms.CharField(widget=forms.Textarea(attrs={'placeholder': "Write review"}))

    class Meta:
        model = ProductReview
        fields = ['review', 'rating']


class KHQRPaymentForm(forms.ModelForm):
    """Proof of a KHQR transfer, submitted by the buyer after they scan the QR."""

    khqr_reference = forms.CharField(
        required=True,
        max_length=100,
        label="Transaction ID",
        widget=forms.TextInput(attrs={'placeholder': "e.g. 100FT2503071234567"}),
    )
    khqr_proof = forms.ImageField(
        required=False,
        label="Payment screenshot (optional)",
    )
    khqr_note = forms.CharField(
        required=False,
        label="Note for the seller (optional)",
        widget=forms.Textarea(attrs={'placeholder': "Anything we should know about this payment", 'rows': 3}),
    )

    class Meta:
        model = CartOrder
        fields = ['khqr_reference', 'khqr_proof', 'khqr_note']

    def clean_khqr_proof(self):
        proof = self.cleaned_data.get("khqr_proof")
        if proof and proof.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Screenshot must be smaller than 5MB.")
        return proof