from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User, Auction

# --- REGISTRATION FORM ---
class CustomUserCreationForm(UserCreationForm):
    # Defining specific fields with widgets for a better UI
    role = forms.ChoiceField(
        choices=[('buyer', 'Buyer'), ('seller', 'Seller')], 
        widget=forms.RadioSelect,
        initial='buyer'
    )
    phone_number = forms.CharField(
        max_length=15, 
        required=True, 
        help_text="Enter your contact number"
    )
    profile_photo = forms.ImageField(
        required=True, 
        help_text="Upload a clear photo of yourself"
    )

    class Meta(UserCreationForm.Meta):
        model = User
        # Combined all fields from both snippets
        fields = UserCreationForm.Meta.fields + (
            'first_name', 
            'last_name', 
            'email', 
            'phone_number', 
            'profile_photo', 
            'role'
        )

    def save(self, commit=True):
        """
        Handles the logic to set is_buyer/is_seller flags 
        based on the 'role' choice during registration.
        """
        user = super().save(commit=False)
        role = self.cleaned_data.get('role')
        
        if role == 'buyer':
            user.is_buyer = True
            user.is_seller = False
        elif role == 'seller':
            user.is_seller = True
            user.is_buyer = False
            
        if commit:
            user.save()
        return user


# --- LOGIN FORM ---
class EmailLoginForm(AuthenticationForm):
    username = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'form-control', 
        'placeholder': 'Email'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control', 
        'placeholder': 'Password'
    }))


# --- PROFILE EDIT FORM ---
class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'profile_photo']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
            'profile_photo': forms.FileInput(attrs={'class': 'form-control'}),
        }


# --- AUCTION CREATION FORM ---
class AuctionListingForm(forms.ModelForm):
    class Meta:
        model = Auction
        fields = ['title', 'description', 'category', 'starting_bid', 'image', 'end_time']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'starting_bid': forms.NumberInput(attrs={'class': 'form-control'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'end_time': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        }