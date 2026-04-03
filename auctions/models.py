from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.validators import MinValueValidator

# --- Custom User Model ---
class User(AbstractUser):
    is_buyer = models.BooleanField(default=False)
    is_seller = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    is_premium = models.BooleanField(default=False) # From updated request
    
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    profile_photo = models.ImageField(upload_to='profile_photos/', blank=True, null=True)
    
    email = models.EmailField(unique=True)
    email_verified = models.BooleanField(default=False)

    # Email as Primary Login ID
    USERNAME_FIELD = 'email' 
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email

# --- Category Model ---
class Category(models.Model):
    name = models.CharField(max_length=100)
    
    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

# --- Auction Model ---
class Auction(models.Model):
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='auctions')
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name="items")
    starting_bid = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    current_highest_bid = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    image = models.ImageField(upload_to='auction_images/')
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField()
    
    is_active = models.BooleanField(default=True)
    winner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='won_auctions')
    transaction_hash = models.CharField(max_length=64, blank=True, null=True)

    def save(self, *args, **kwargs):
        # Automatically set current bid to starting bid if it's a new auction
        if not self.current_highest_bid:
            self.current_highest_bid = self.starting_bid
        super().save(*args, **kwargs)

    def get_highest_bid(self):
        # Finds the single highest bid for this auction
        return self.bids.order_by('-amount').first()
    
    def is_finished(self):
        """Check if the auction has passed its end_time"""
        if self.end_time:
            return timezone.now() > self.end_time
        return False

    @property
    def auto_winner(self):
        """Identify the winner based on the highest bid"""
        if self.is_finished:
            # Assumes your Bid model has a related_name='bids'
            highest_bid = self.bids.order_by('-amount').first()
            return highest_bid.bidder if highest_bid else None
        return None

# --- Bidding System ---
class Bid(models.Model):
    auction = models.ForeignKey(Auction, on_delete=models.CASCADE, related_name='bids')
    bidder = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-amount']

    def __str__(self):
        return f"{self.bidder.username} bid ${self.amount} on {self.auction.title}"

# --- Logs & Security ---
class SecurityLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE) 
    action = models.CharField(max_length=255)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_suspicious = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.email} - {self.action} at {self.timestamp}"

# --- Financials ---
class Payment(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending Escrow'),
        ('RELEASED', 'Released to Seller'),
        ('REFUNDED', 'Refunded to Buyer'),
    ]
    auction = models.OneToOneField(Auction, on_delete=models.CASCADE, related_name='payment')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_id = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

# --- Dispute Management ---
class Dispute(models.Model):
    auction = models.ForeignKey(Auction, on_delete=models.CASCADE)
    complainant = models.ForeignKey(User, on_delete=models.CASCADE)
    reason = models.TextField()
    is_resolved = models.BooleanField(default=False)
    admin_notes = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)