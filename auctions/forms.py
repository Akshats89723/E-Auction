from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.forms import inlineformset_factory
from .models import User, Auction, AuctionImage, AutoBid, Dispute


# ─── REGISTRATION ────────────────────────────────────────────────────────────

class CustomUserCreationForm(UserCreationForm):
    role = forms.ChoiceField(
        choices=[('buyer', 'Buyer'), ('seller', 'Seller')],
        widget=forms.RadioSelect,
        initial='buyer',
    )
    phone_number = forms.CharField(
        max_length=15, required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+91 9876543210'}),
    )
    profile_photo = forms.ImageField(
        required=True,
        widget=forms.FileInput(attrs={'class': 'form-control'}),
    )
    bio = forms.CharField(
        max_length=300, required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control', 'rows': 2,
            'placeholder': 'Tell buyers/sellers about yourself (optional)…',
        }),
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + (
            'first_name', 'last_name', 'email',
            'phone_number', 'profile_photo', 'bio', 'role',
        )

    def save(self, commit=True):
        user = super().save(commit=False)
        role = self.cleaned_data.get('role')
        user.is_buyer = role == 'buyer'
        user.is_seller = role == 'seller'
        if commit:
            user.save()
        return user


# ─── LOGIN ────────────────────────────────────────────────────────────────────

class EmailLoginForm(AuthenticationForm):
    username = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'form-control py-2',
        'placeholder': 'your@email.com',
        'autocomplete': 'email',
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control py-2',
        'placeholder': 'Enter password',
        'autocomplete': 'current-password',
    }))



# ─── PROFILE EDIT ─────────────────────────────────────────────────────────────

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone_number', 'bio', 'profile_photo']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'profile_photo': forms.FileInput(attrs={'class': 'form-control'}),
        }


# ─── AUCTION CREATION ─────────────────────────────────────────────────────────

class AuctionListingForm(forms.ModelForm):
    class Meta:
        model = Auction
        fields = [
            'title', 'description', 'category', 'starting_bid',
            'reserve_price', 'buy_now_price', 'min_bid_increment',
            'image', 'end_time', 'model_3d', 'is_private',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Item title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'starting_bid': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'reserve_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'buy_now_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'min_bid_increment': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'end_time': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'model_3d': forms.FileInput(attrs={'class': 'form-control', 'accept': '.glb,.gltf'}),
            'is_private': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        help_texts = {
            'reserve_price': 'Hidden minimum. Auction only sells if this is met.',
            'buy_now_price': 'Optional. Buyer can win immediately at this price.',
            'min_bid_increment': 'Minimum amount each new bid must exceed current by.',
            'model_3d': 'Optional. Upload a .glb or .gltf 3D model for interactive viewing.',
            'is_private': 'Only Gold and Platinum members will see this auction.',
        }


# ─── ADDITIONAL AUCTION IMAGES (inline formset) ───────────────────────────────

class AuctionImageForm(forms.ModelForm):
    class Meta:
        model = AuctionImage
        fields = ['image', 'caption']
        widgets = {
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'caption': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional caption'}),
        }

# Allow up to 5 extra images per auction
AuctionImageFormSet = inlineformset_factory(
    Auction, AuctionImage,
    form=AuctionImageForm,
    extra=3, max_num=5, can_delete=False,
)


# ─── AUTO BID ─────────────────────────────────────────────────────────────────

class AutoBidForm(forms.ModelForm):
    class Meta:
        model = AutoBid
        fields = ['max_amount']
        widgets = {
            'max_amount': forms.NumberInput(attrs={
                'class': 'form-control form-control-lg',
                'step': '0.01',
                'placeholder': 'Maximum amount you are willing to pay',
            }),
        }
        labels = {'max_amount': 'Your Maximum Bid (₹)'}


# ─── DISPUTE ──────────────────────────────────────────────────────────────────

class DisputeForm(forms.ModelForm):
    class Meta:
        model = Dispute
        fields = ['reason']
        widgets = {
            'reason': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 5,
                'placeholder': 'Describe the issue clearly…',
            }),
        }
