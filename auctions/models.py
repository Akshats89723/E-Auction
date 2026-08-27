from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Avg
import datetime

# --- Custom User Model ---
class User(AbstractUser):
    is_buyer = models.BooleanField(default=False)
    is_seller = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    is_premium = models.BooleanField(default=False)
    
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    profile_photo = models.ImageField(upload_to='profile_photos/', blank=True, null=True)
    bio = models.TextField(blank=True, help_text="Short description about yourself")
    
    email = models.EmailField(unique=True)
    email_verified = models.BooleanField(default=False)
    verification_token = models.CharField(max_length=100, blank=True, null=True)
    
    # 2FA
    two_factor_enabled = models.BooleanField(default=False)
    two_factor_secret = models.CharField(max_length=32, blank=True, null=True)

    # Gamification
    xp = models.PositiveIntegerField(default=0)

    # Email as Primary Login ID
    USERNAME_FIELD = 'email' 
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email
    
    @property
    def average_rating(self):
        """Calculate average rating from reviews received"""
        avg = self.reviews_received.aggregate(Avg('rating'))['rating__avg']
        return round(avg, 1) if avg else None
    
    @property
    def total_reviews(self):
        """Total number of reviews received"""
        return self.reviews_received.count()

    @property
    def vip_tier(self):
        if self.xp >= 5000:
            return 'Platinum'
        elif self.xp >= 2000:
            return 'Gold'
        elif self.xp >= 500:
            return 'Silver'
        return 'Bronze'

# --- Category Model ---
class Category(models.Model):
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=50, blank=True, default='bi-tag', help_text="Bootstrap Icons class e.g. bi-laptop")
    
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
    
    # Reserve & Buy Now prices
    reserve_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Minimum price required to sell. Hidden from buyers.")
    buy_now_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Price at which buyer can immediately win the auction.")
    
    # Minimum bid increment (e.g. must bid at least +50)
    min_bid_increment = models.DecimalField(max_digits=8, decimal_places=2, default=1.00,
        validators=[MinValueValidator(0.01)])

    image = models.ImageField(upload_to='auction_images/')
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField()
    
    is_active = models.BooleanField(default=True)
    is_draft = models.BooleanField(default=False, help_text="Save without publishing")
    is_private = models.BooleanField(default=False, help_text="Only visible to Gold/Platinum members")
    model_3d = models.FileField(upload_to='3d_models/', blank=True, null=True, help_text="Upload .glb or .gltf files for 3D viewing")
    winner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='won_auctions')
    transaction_hash = models.CharField(max_length=64, blank=True, null=True)
    
    # For auto-bid tracking
    views_count = models.PositiveIntegerField(default=0)

    def save(self, *args, **kwargs):
        if not self.current_highest_bid:
            self.current_highest_bid = self.starting_bid
        super().save(*args, **kwargs)

    def get_highest_bid(self):
        return self.bids.order_by('-amount').first()

    @property
    def is_finished(self):
        if self.end_time:
            return timezone.now() > self.end_time
        return False

    @property
    def reserve_met(self):
        """Check if current bid has met the reserve price"""
        if not self.reserve_price:
            return True
        return self.current_highest_bid >= self.reserve_price

    @property
    def get_winner(self):
        if self.is_finished:
            highest_bid = self.bids.order_by('-amount').first()
            if highest_bid:
                # Only assign winner if reserve price is met
                if self.reserve_met:
                    return highest_bid.bidder
        return None

    def increment_views(self):
        Auction.objects.filter(pk=self.pk).update(views_count=models.F('views_count') + 1)

    def __str__(self):
        return self.title
# --- Bidding System ---
class Bid(models.Model):
    auction = models.ForeignKey(Auction, on_delete=models.CASCADE, related_name='bids')
    bidder = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_auto_bid = models.BooleanField(default=False, help_text="Was this placed by the auto-bidder?")

    class Meta:
        ordering = ['-amount']

    def __str__(self):
        return f"{self.bidder.username} bid ₹{self.amount} on {self.auction.title}"


# --- Auto Bidding ---
class AutoBid(models.Model):
    """Proxy bidding: user sets a max amount, system auto-bids for them"""
    auction = models.ForeignKey(Auction, on_delete=models.CASCADE, related_name='auto_bids')
    bidder = models.ForeignKey(User, on_delete=models.CASCADE, related_name='auto_bids')
    max_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('auction', 'bidder')

    def __str__(self):
        return f"{self.bidder.username} auto-bid up to ₹{self.max_amount} on {self.auction.title}"


# --- Auction Images (Multiple images per auction) ---
class AuctionImage(models.Model):
    auction = models.ForeignKey(Auction, on_delete=models.CASCADE, related_name='additional_images')
    image = models.ImageField(upload_to='auction_images/')
    caption = models.CharField(max_length=200, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Image for {self.auction.title}"

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
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment {self.transaction_id} - {self.status}"

# --- Dispute Management ---
class Dispute(models.Model):
    auction = models.ForeignKey(Auction, on_delete=models.CASCADE)
    complainant = models.ForeignKey(User, on_delete=models.CASCADE)
    reason = models.TextField()
    is_resolved = models.BooleanField(default=False)
    admin_notes = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

class Order(models.Model):
    STATUS_CHOICES = [
        ('PROCESSING', 'Processing'),
        ('SHIPPED', 'Shipped'),
        ('OUT_FOR_DELIVERY', 'Out for Delivery'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
    ]
    auction = models.OneToOneField(Auction, related_name='order', on_delete=models.CASCADE)
    winner = models.ForeignKey(User, on_delete=models.CASCADE)
    delivery_address = models.TextField()
    city = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    order_date = models.DateTimeField(auto_now_add=True)
    estimated_delivery = models.DateField(null=True, blank=True)
    is_delivered = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PROCESSING')
    tracking_number = models.CharField(max_length=100, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.estimated_delivery:
            self.estimated_delivery = datetime.date.today() + datetime.timedelta(days=7)
        # Sync is_delivered with status
        if self.status == 'DELIVERED':
            self.is_delivered = True
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order #{self.id} - {self.auction.title}"

# --- Watchlist System ---
class Watchlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='watchlist')
    auction = models.ForeignKey(Auction, on_delete=models.CASCADE, related_name='watchers')
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'auction')

    def __str__(self):
        return f"{self.user.username} watching {self.auction.title}"

# --- Notification System ---
class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    link = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"Notification for {self.user.username}: {self.message[:20]}"

# --- Reputation & Review System ---
class Review(models.Model):
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_given')
    reviewee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_received')
    auction = models.OneToOneField(Auction, on_delete=models.CASCADE, related_name='review')
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.reviewer.username} rated {self.reviewee.username} {self.rating} stars"

