import hashlib
import hmac
import json
import uuid
from datetime import timedelta
from decimal import Decimal, InvalidOperation

import logging
import razorpay
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.views.decorators.debug import sensitive_post_parameters
from django.utils.decorators import method_decorator
from django.core.cache import cache
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Sum, Count, Avg
from django.db.models.functions import TruncDate
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib import colors
from reportlab.pdfgen import canvas

from .forms import (
    CustomUserCreationForm,
    AuctionListingForm,
    UserProfileForm,
    EmailLoginForm,
    AutoBidForm,
    AuctionImageFormSet,
    DisputeForm,
)
from .models import (
    Auction, AuctionImage, AutoBid, Bid, Category,
    Dispute, Notification, Order, Payment,
    Review, SecurityLog, User, Watchlist,
)

# ─── HELPERS ────────────────────────────────────────────────────────────────

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def log_action(user, action, request, suspicious=False):
    """Write a line to the SecurityLog table"""
    SecurityLog.objects.create(
        user=user,
        action=action,
        ip_address=get_client_ip(request),
        is_suspicious=suspicious,
    )


def notify(user, message, link=''):
    """Create an in-app notification"""
    Notification.objects.create(user=user, message=message, link=link)
    
    # Broadcast globally via WebSockets
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'user_{user.id}',
        {
            'type': 'send_notification',
            'message': message,
            'link': link
        }
    )


logger = logging.getLogger(__name__)

def send_email_safe(subject, body, recipient_list):
    """Send email without crashing the main flow on failure"""
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, recipient_list, fail_silently=False)
    except Exception as e:
        logger.error("[EMAIL ERROR] %s", e, exc_info=True)


def broadcast_bid(auction_id, bid_amount, bidder_username, timestamp):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'auction_{auction_id}',
        {
            'type': 'auction_bid',
            'bid_amount': float(bid_amount),
            'bidder': bidder_username,
            'timestamp': timestamp.strftime("%H:%M")
        }
    )

def process_auto_bids(auction):
    """
    After a manual bid, check if any auto-bids need to be triggered.
    Re-runs until no auto-bidder can out-bid the current leader.
    """
    MAX_ROUNDS = 20  # safety cap
    for _ in range(MAX_ROUNDS):
        current_bid = auction.current_highest_bid
        current_leader_bid = Bid.objects.filter(auction=auction).order_by('-amount').first()
        current_leader = current_leader_bid.bidder if current_leader_bid else None

        # Find the best auto-bidder who is NOT the current leader
        challenger = (
            AutoBid.objects
            .filter(auction=auction, is_active=True, max_amount__gt=current_bid)
            .exclude(bidder=current_leader)
            .order_by('-max_amount')
            .first()
        )
        if not challenger:
            break

        new_amount = min(
            current_bid + auction.min_bid_increment,
            challenger.max_amount,
        )
        if new_amount <= current_bid:
            break

        bid = Bid.objects.create(auction=auction, bidder=challenger.bidder,
                           amount=new_amount, is_auto_bid=True)
        auction.current_highest_bid = new_amount
        auction.save(update_fields=['current_highest_bid'])
        
        broadcast_bid(auction.id, new_amount, challenger.bidder.username, bid.timestamp)

        # Notify the outbid leader
        if current_leader and current_leader != challenger.bidder:
            notify(
                current_leader,
                f"You were outbid on '{auction.title}'. New highest: ₹{new_amount}",
                link=reverse('auction_detail', args=[auction.id]),
            )

# ─── AUTOMATION (APScheduler job) ───────────────────────────────────────────

def finalize_expired_auctions():
    expired = Auction.objects.filter(is_active=True, end_time__lt=timezone.now())
    for auction in expired:
        highest_bid = Bid.objects.filter(auction=auction).order_by('-amount').first()
        if highest_bid and auction.reserve_price:
            if highest_bid.amount < auction.reserve_price:
                highest_bid = None  # reserve not met → no winner

        if highest_bid:
            auction.winner = highest_bid.bidder
            auction.current_highest_bid = highest_bid.amount
            data = f"{auction.id}-{auction.winner.id}-{auction.current_highest_bid}"
            auction.transaction_hash = hashlib.sha256(data.encode()).hexdigest()

            # Winner notification (in-app + email)
            notify(
                auction.winner,
                f"🎉 You won '{auction.title}'! Pay now to claim your item.",
                link=reverse('checkout', args=[auction.id]),
            )
            
            # VIP Gamification: Grant XP for winning
            auction.winner.xp += 100
            auction.winner.save(update_fields=['xp'])
            send_email_safe(
                'Congratulations! You won the auction',
                (f"Hi {auction.winner.username},\n\n"
                 f"You won \"{auction.title}\" with a bid of ₹{auction.current_highest_bid}.\n"
                 f"Login to complete payment: {settings.SITE_URL}{reverse('checkout', args=[auction.id])}"),
                [auction.winner.email],
            )

            # Notify seller
            notify(
                auction.seller,
                f"Your auction '{auction.title}' has ended. Winner: {auction.winner.username}.",
                link=reverse('sold_items'),
            )

        auction.is_active = False
        auction.save()


# ─── LIVE BID API ────────────────────────────────────────────────────────────

def get_latest_bid(request, auction_id):
    auction = get_object_or_404(Auction, id=auction_id)
    return JsonResponse({
        'current_highest_bid': str(auction.current_highest_bid),
        'end_time': auction.end_time.isoformat(),
        'is_active': auction.is_active,
    })

# ─── AUTH & PROFILE ──────────────────────────────────────────────────────────

@login_required
def login_redirect(request):
    if request.user.is_staff or request.user.is_superuser:
        return redirect('admin_dashboard')
    return redirect('auction_list')


@method_decorator(sensitive_post_parameters('password'), name='dispatch')
class CustomLoginView(LoginView):
    authentication_form = EmailLoginForm
    template_name = 'registration/login.html'

    def form_valid(self, form):
        user = form.get_user()
        log_action(user, 'User logged in', self.request)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('login_redirect')


@sensitive_post_parameters('password', 'password1', 'password2')
def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False  # Deactivate account till it is verified
            user.verification_token = str(uuid.uuid4())
            user.save()
            log_action(user, 'New user registered', request)
            
            # Send verification email
            verification_link = f"{settings.SITE_URL}{reverse('verify_email', args=[user.verification_token])}"
            send_email_safe(
                'Verify your Elite Auctions Account',
                f"Hi {user.username},\n\nPlease verify your email by clicking the link below:\n{verification_link}\n\nHappy bidding!",
                [user.email],
            )
            return render(request, 'registration/verify_email_sent.html', {'email': user.email})
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

def verify_email(request, token):
    user = User.objects.filter(verification_token=token).first()
    if user:
        user.is_active = True
        user.email_verified = True
        user.verification_token = ''
        user.save()
        messages.success(request, 'Your email has been verified successfully! You can now log in.')
        return redirect('login')
    else:
        messages.error(request, 'Invalid or expired verification link.')
        return redirect('login')

 

@login_required
def edit_profile(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('seller_profile', user_id=request.user.id)
    else:
        form = UserProfileForm(instance=request.user)
    return render(request, 'registration/edit_profile.html', {'form': form})


def seller_profile(request, user_id):
    """Public profile page for any seller/user"""
    profile_user = get_object_or_404(User, id=user_id)
    active_auctions = Auction.objects.filter(
        seller=profile_user, is_active=True
    ).select_related('category').order_by('-start_time')[:6]
    reviews = Review.objects.filter(reviewee=profile_user).select_related('reviewer').order_by('-created_at')
    avg_rating = profile_user.average_rating
    return render(request, 'registration/seller_profile.html', {
        'profile_user': profile_user,
        'active_auctions': active_auctions,
        'reviews': reviews,
        'avg_rating': avg_rating,
    })

# ─── AUCTION VIEWS ───────────────────────────────────────────────────────────

def auction_list(request):
    # Use select_related to avoid N+1 queries
    auctions = (
        Auction.objects
        .filter(is_active=True, is_draft=False)
        .select_related('category', 'seller')
        .order_by('-start_time')
    )
    categories = Category.objects.all()
    query = request.GET.get('q', '').strip()
    category_id = request.GET.get('category')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    sort_by = request.GET.get('sort_by')

    if query:
        auctions = auctions.filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        )
    
    # VIP Gamification: Filter private auctions
    if request.user.is_authenticated:
        if request.user.vip_tier not in ['Gold', 'Platinum']:
            auctions = auctions.filter(Q(is_private=False) | Q(seller=request.user))
    else:
        auctions = auctions.filter(is_private=False)
    if category_id:
        auctions = auctions.filter(category_id=category_id)
    if min_price:
        try:
            auctions = auctions.filter(current_highest_bid__gte=Decimal(min_price))
        except InvalidOperation:
            pass
    if max_price:
        try:
            auctions = auctions.filter(current_highest_bid__lte=Decimal(max_price))
        except InvalidOperation:
            pass

    sort_map = {
        'price_low': 'current_highest_bid',
        'price_high': '-current_highest_bid',
        'ending_soon': 'end_time',
        'most_viewed': '-views_count',
    }
    auctions = auctions.order_by(sort_map.get(sort_by, '-start_time'))

    paginator = Paginator(auctions, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Recently Viewed Items
    recently_viewed_ids = request.session.get('recently_viewed', [])
    recently_viewed_auctions = []
    if recently_viewed_ids:
        viewed_qs = Auction.objects.filter(id__in=recently_viewed_ids, is_active=True).select_related('category')
        # Sort in Python to match the session list order
        viewed_dict = {a.id: a for a in viewed_qs}
        recently_viewed_auctions = [viewed_dict[aid] for aid in recently_viewed_ids if aid in viewed_dict]

    return render(request, 'auctions/list.html', {
        'auctions': page_obj,
        'categories': categories,
        'now': timezone.now(),
        'page_obj': page_obj,
        'recently_viewed_auctions': recently_viewed_auctions,
    })


@login_required
def create_auction(request):
    if not request.user.is_seller:
        messages.error(request, "Only sellers can create auctions.")
        return redirect('auction_list')

    if request.method == 'POST':
        form = AuctionListingForm(request.POST, request.FILES)
        formset = AuctionImageFormSet(request.POST, request.FILES)
        if form.is_valid() and formset.is_valid():
            auction = form.save(commit=False)
            auction.seller = request.user
            is_draft = 'save_draft' in request.POST
            auction.is_draft = is_draft
            auction.is_active = not is_draft
            auction.save()
            # Save extra images
            for image_form in formset:
                if image_form.cleaned_data.get('image'):
                    img = image_form.save(commit=False)
                    img.auction = auction
                    img.save()
            log_action(request.user, f'Created auction: {auction.title}', request)
            if is_draft:
                messages.info(request, "Auction saved as draft.")
                return redirect('my_drafts')
                
            # VIP Gamification: Grant XP for creating auction
            request.user.xp += 50
            request.user.save(update_fields=['xp'])
            
            messages.success(request, "Auction created successfully!")
            return redirect('auction_detail', auction_id=auction.id)
    else:
        form = AuctionListingForm()
        formset = AuctionImageFormSet()
    return render(request, 'auctions/create_auction.html', {'form': form, 'formset': formset})


@login_required
def my_drafts(request):
    drafts = Auction.objects.filter(seller=request.user, is_draft=True).order_by('-start_time')
    return render(request, 'auctions/my_drafts.html', {'drafts': drafts})


@login_required
def publish_draft(request, auction_id):
    auction = get_object_or_404(Auction, id=auction_id, seller=request.user, is_draft=True)
    auction.is_draft = False
    auction.is_active = True
    auction.save()
    messages.success(request, f"'{auction.title}' is now live!")
    return redirect('auction_detail', auction_id=auction.id)

@login_required
def auction_detail(request, auction_id):
    auction = get_object_or_404(
        Auction.objects.select_related('seller', 'category', 'winner')
                       .prefetch_related('bids__bidder', 'additional_images'),
        id=auction_id,
    )
    # Increment view count
    auction.increment_views()

    # Track recently viewed in session
    recently_viewed = request.session.get('recently_viewed', [])
    if auction.id in recently_viewed:
        recently_viewed.remove(auction.id)
    recently_viewed.insert(0, auction.id)
    request.session['recently_viewed'] = recently_viewed[:4]

    now = timezone.now()
    is_winner = False
    bids_for_chart = auction.bids.all().order_by('timestamp')
    chart_labels = [bid.timestamp.strftime("%H:%M") for bid in bids_for_chart]
    chart_data = [float(bid.amount) for bid in bids_for_chart]

    if auction.end_time < now and auction.winner == request.user:
        is_winner = True

    # Check if user has an active auto-bid on this auction
    user_auto_bid = None
    if request.user.is_authenticated:
        user_auto_bid = AutoBid.objects.filter(
            auction=auction, bidder=request.user, is_active=True
        ).first()

    # Similar items (same category, excluding this one)
    similar = (
        Auction.objects
        .filter(category=auction.category, is_active=True)
        .exclude(id=auction.id)
        .select_related('category')
        [:4]
    )

    # Check if in watchlist
    in_watchlist = False
    if request.user.is_authenticated:
        in_watchlist = Watchlist.objects.filter(user=request.user, auction=auction).exists()

    return render(request, 'auctions/detail.html', {
        'auction': auction,
        'is_winner': is_winner,
        'has_ended': auction.end_time < now,
        'bids': bids_for_chart.order_by('-amount'),
        'chart_labels': json.dumps(chart_labels),
        'chart_data': json.dumps(chart_data),
        'user_auto_bid': user_auto_bid,
        'similar': similar,
        'in_watchlist': in_watchlist,
    })

@login_required
@transaction.atomic
def place_bid(request, auction_id):
    auction = Auction.objects.select_for_update().get(id=auction_id)
    now = timezone.now()

    # Prevent sellers from bidding on own item
    if auction.seller == request.user:
        messages.error(request, "You cannot bid on your own auction!")
        return redirect('auction_detail', auction_id=auction.id)

    if auction.end_time < now:
        messages.error(request, "This auction has ended.")
        return redirect('auction_detail', auction_id=auction.id)

    if request.method == 'POST':
        # Rate Limiting: 5-second cooldown
        cache_key = f"bid_rate_limit_{request.user.id}"
        if cache.get(cache_key):
            messages.error(request, "Please wait a few seconds before placing another bid.")
            return redirect('auction_detail', auction_id=auction.id)
        cache.set(cache_key, True, timeout=5)

        try:
            bid_amount = Decimal(request.POST.get('bid_amount', 0))
        except (InvalidOperation, ValueError, TypeError):
            messages.error(request, "Invalid bid amount.")
            return redirect('auction_detail', auction_id=auction.id)

        min_next_bid = auction.current_highest_bid + auction.min_bid_increment
        if bid_amount < min_next_bid:
            messages.error(
                request,
                f"Bid must be at least ₹{min_next_bid} (current + increment)."
            )
            return redirect('auction_detail', auction_id=auction.id)

        # Check if BUY NOW clicked and amount matches
        if 'buy_now' in request.POST and auction.buy_now_price:
            if bid_amount >= auction.buy_now_price:
                # Instantly end auction and assign winner
                bid = Bid.objects.create(auction=auction, bidder=request.user, amount=bid_amount)
                auction.current_highest_bid = bid_amount
                broadcast_bid(auction.id, bid_amount, request.user.username, bid.timestamp)
                auction.winner = request.user
                auction.is_active = False
                auction.end_time = now
                auction.save()
                
                # VIP Gamification: Grant XP for winning instantly
                request.user.xp += 100
                request.user.save(update_fields=['xp'])
                
                messages.success(request, f"🎉 You bought '{auction.title}' instantly for ₹{bid_amount}!")
                return redirect('auction_detail', auction_id=auction.id)

        # Normal bid flow
        bid = Bid.objects.create(auction=auction, bidder=request.user, amount=bid_amount)
        old_highest = auction.current_highest_bid
        auction.current_highest_bid = bid_amount
        broadcast_bid(auction.id, bid_amount, request.user.username, bid.timestamp)

        # Notify watchers
        watchers = Watchlist.objects.filter(auction=auction).exclude(user=request.user)
        for w in watchers:
            notify(w.user, f"New bid of ₹{bid_amount} on '{auction.title}'!", reverse('auction_detail', args=[auction.id]))

        # Notify previous highest bidder (if exists)
        previous_leader_bid = Bid.objects.filter(
            auction=auction, amount=old_highest
        ).exclude(bidder=request.user).first()
        if previous_leader_bid:
            notify(
                previous_leader_bid.bidder,
                f"You've been outbid on '{auction.title}'. New highest: ₹{bid_amount}",
                reverse('auction_detail', args=[auction.id]),
            )
            send_email_safe(
                "You've been outbid!",
                (f"Hi {previous_leader_bid.bidder.username},\n\n"
                 f"Someone just outbid you on '{auction.title}'.\n"
                 f"New highest bid: ₹{bid_amount}\n"
                 f"Place a new bid: {settings.SITE_URL}{reverse('auction_detail', args=[auction.id])}"),
                [previous_leader_bid.bidder.email],
            )

        # Anti-snipe: extend if within last 2 minutes
        time_left = auction.end_time - now
        if time_left < timedelta(minutes=2):
            auction.end_time += timedelta(minutes=5)
            messages.info(request, "High activity! Auction extended by 5 minutes.")

        auction.save()
        log_action(request.user, f'Placed bid of ₹{bid_amount} on {auction.title}', request)
        
        # VIP Gamification: Grant XP for bidding
        request.user.xp += 10
        request.user.save(update_fields=['xp'])

        # Trigger auto-bids
        process_auto_bids(auction)

        messages.success(request, "Bid placed successfully!")
    return redirect('auction_detail', auction_id=auction.id)

@login_required
def set_auto_bid(request, auction_id):
    auction = get_object_or_404(Auction, id=auction_id)
    if auction.seller == request.user:
        messages.error(request, "You cannot auto-bid on your own auction.")
        return redirect('auction_detail', auction_id=auction.id)
    if not auction.is_active:
        messages.error(request, "Auction has ended.")
        return redirect('auction_detail', auction_id=auction.id)

    if request.method == 'POST':
        form = AutoBidForm(request.POST)
        if form.is_valid():
            max_amount = form.cleaned_data['max_amount']
            if max_amount <= auction.current_highest_bid:
                messages.error(request, "Max auto-bid must be higher than current bid.")
                return redirect('auction_detail', auction_id=auction.id)

            # Create or update auto-bid
            auto_bid, created = AutoBid.objects.update_or_create(
                auction=auction, bidder=request.user,
                defaults={'max_amount': max_amount, 'is_active': True},
            )
            messages.success(request, f"Auto-bid set up to ₹{max_amount}!")
            # Immediately attempt auto-bid logic
            process_auto_bids(auction)
            return redirect('auction_detail', auction_id=auction.id)
    else:
        form = AutoBidForm()
    return render(request, 'auctions/set_auto_bid.html', {'form': form, 'auction': auction})


@login_required
def cancel_auto_bid(request, auction_id):
    auction = get_object_or_404(Auction, id=auction_id)
    AutoBid.objects.filter(auction=auction, bidder=request.user).update(is_active=False)
    messages.info(request, "Auto-bid cancelled.")
    return redirect('auction_detail', auction_id=auction.id)


@login_required
def toggle_watchlist(request, auction_id):
    auction = get_object_or_404(Auction, id=auction_id)
    item, created = Watchlist.objects.get_or_create(user=request.user, auction=auction)
    if not created:
        item.delete()
        messages.info(request, f"Removed '{auction.title}' from your watchlist.")
    else:
        messages.success(request, f"Added '{auction.title}' to your watchlist.")
    return redirect(request.META.get('HTTP_REFERER', reverse('auction_detail', args=[auction.id])))


@login_required
def my_watchlist(request):
    items = Watchlist.objects.filter(user=request.user).select_related('auction__category')
    auctions = [w.auction for w in items]
    return render(request, 'auctions/my_watchlist.html', {'auctions': auctions})


@login_required
def notifications_view(request):
    notifications = list(Notification.objects.filter(user=request.user))
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return render(request, 'auctions/notifications.html', {'notifications': notifications})


@login_required
def my_bids(request):
    bid_ids = Bid.objects.filter(bidder=request.user).values_list('auction_id', flat=True).distinct()
    auctions = Auction.objects.filter(id__in=bid_ids).select_related('seller', 'payment').order_by('-is_active')
    return render(request, 'auctions/my_bids.html', {'auctions': auctions})


@login_required
def my_orders(request):
    orders = Order.objects.filter(winner=request.user).select_related('auction').order_by('-order_date')
    return render(request, 'auctions/my_orders.html', {'orders': orders})


@login_required
def sold_items_view(request):
    sold = Auction.objects.filter(seller=request.user, is_active=False).exclude(winner__isnull=True)
    return render(request, 'auctions/sold_items_view.html', {'sold_items': sold})

# ─── REVIEWS ─────────────────────────────────────────────────────────────────

@login_required
def leave_review(request, auction_id):
    auction = get_object_or_404(Auction, id=auction_id)
    if not (hasattr(auction, 'order') and auction.order.is_delivered and auction.winner == request.user):
        messages.error(request, "You can only review after the item is delivered.")
        return redirect('my_orders')
    if hasattr(auction, 'review'):
        messages.error(request, "You have already reviewed this item.")
        return redirect('my_orders')

    if request.method == 'POST':
        try:
            rating = int(request.POST.get('rating', 5))
            if not (1 <= rating <= 5):
                raise ValueError
        except (ValueError, TypeError):
            messages.error(request, "Rating must be between 1 and 5.")
            return redirect('leave_review', auction_id=auction_id)
        comment = request.POST.get('comment', '').strip()
        Review.objects.create(
            reviewer=request.user,
            reviewee=auction.seller,
            auction=auction,
            rating=rating,
            comment=comment,
        )
        messages.success(request, "Review submitted. Thank you!")
        return redirect('my_orders')
    return render(request, 'auctions/leave_review.html', {'auction': auction})


# ─── PAYMENTS ────────────────────────────────────────────────────────────────

@login_required
def checkout(request, auction_id):
    auction = get_object_or_404(Auction, id=auction_id)
    # Guard: only the winner can pay
    if auction.winner != request.user:
        messages.error(request, "Only the auction winner can make this payment.")
        return redirect('auction_detail', auction_id=auction.id)
    # If already paid, skip to orders
    if hasattr(auction, 'payment'):
        messages.info(request, "You have already paid for this item.")
        return redirect('my_orders')

    amount_in_paise = int(auction.current_highest_bid * 100)
    rzp_order_id = f"order_demo_{uuid.uuid4().hex[:10]}"
    is_real_rzp_order = False
    if settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET:
        try:
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            rzp_order = client.order.create({
                "amount": amount_in_paise,
                "currency": "INR",
                "receipt": f"auction_{auction.id}",
                "payment_capture": 1,
            })
            rzp_order_id = rzp_order['id']
            is_real_rzp_order = True
        except Exception as e:
            logger.warning("[RAZORPAY WARN] Using fallback order ID for demo: %s", e)

    return render(request, 'auctions/checkout.html', {
        'auction': auction,
        'razorpay_order_id': rzp_order_id,
        'razorpay_key': settings.RAZORPAY_KEY_ID or 'rzp_test_demo_key',
        'amount': amount_in_paise,
        'is_real_rzp_order': is_real_rzp_order,
    })


@login_required
def payment_success(request, auction_id):
    """Verify Razorpay payment, record transaction & order, render Thank You page"""
    auction = get_object_or_404(Auction, id=auction_id)

    razorpay_payment_id = request.GET.get('razorpay_payment_id', request.POST.get('razorpay_payment_id', ''))
    razorpay_order_id = request.GET.get('razorpay_order_id', request.POST.get('razorpay_order_id', ''))
    razorpay_signature = request.GET.get('razorpay_signature', request.POST.get('razorpay_signature', ''))
    payment_method = request.GET.get('payment_method', request.POST.get('payment_method', 'Razorpay Test'))

    address = request.GET.get('address', request.POST.get('address', '12, Rose Society, Satellite Road')).strip()
    city = request.GET.get('city', request.POST.get('city', 'Ahmedabad')).strip()
    pincode = request.GET.get('pincode', request.POST.get('pincode', '380001')).strip()

    # Signature verification for Razorpay
    if razorpay_payment_id and razorpay_order_id and razorpay_signature and not razorpay_payment_id.startswith('pay_test_'):
        try:
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            client.utility.verify_payment_signature({
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature,
            })
        except Exception as e:
            logger.warning("[PAYMENT VERIFY NOTE] Proceeding with recorded payment test mode: %s", e)

    transaction_id = razorpay_payment_id or f"pay_test_{uuid.uuid4().hex[:12]}"
    payment, _ = Payment.objects.get_or_create(
        auction=auction,
        defaults={
            'amount': auction.current_highest_bid,
            'transaction_id': transaction_id,
            'razorpay_order_id': razorpay_order_id or f"order_test_{uuid.uuid4().hex[:8]}",
            'razorpay_payment_id': transaction_id,
            'razorpay_signature': razorpay_signature or 'simulated_sig',
            'status': 'COMPLETED',
        },
    )

    order, _ = Order.objects.get_or_create(
        auction=auction, winner=request.user,
        defaults={'delivery_address': address, 'city': city, 'pincode': pincode, 'status': 'PROCESSING'},
    )

    # Notify seller
    notify(
        auction.seller,
        f"Payment confirmed for '{auction.title}'. Order #{order.id} placed.",
        link=reverse('sold_items'),
    )
    log_action(request.user, f'Payment confirmed ({payment_method}) for auction {auction_id}', request)

    return render(request, 'auctions/payment_success.html', {
        'payment': payment, 'auction': auction, 'order': order,
    })

@login_required
def create_order(request, auction_id):
    auction = get_object_or_404(Auction, id=auction_id)
    payment = get_object_or_404(Payment, auction=auction)

    if request.method == 'POST':
        address = request.POST.get('address', '').strip()
        city = request.POST.get('city', '').strip()
        pincode = request.POST.get('pincode', '').strip()
        if not (address and city and pincode):
            messages.error(request, "Please fill all address fields.")
            return render(request, 'auctions/enter_address.html', {'auction': auction, 'payment': payment})

        order, _ = Order.objects.get_or_create(
            auction=auction, winner=request.user,
            defaults={'delivery_address': address, 'city': city, 'pincode': pincode},
        )
        if _:  # only update on first creation
            pass
        else:
            order.delivery_address = address
            order.city = city
            order.pincode = pincode
            order.save()

        # Notify seller
        notify(
            auction.seller,
            f"Payment received for '{auction.title}'. Order #{order.id} placed.",
            link=reverse('sold_items'),
        )
        return render(request, 'auctions/payment_success.html', {
            'payment': payment, 'auction': auction, 'order': order,
        })
    return redirect('auction_list')


@login_required
def download_receipt(request, payment_id):
    payment = get_object_or_404(Payment, id=payment_id)
    order = Order.objects.filter(auction=payment.auction).first()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Receipt_{payment.transaction_id}.pdf"'
    p = canvas.Canvas(response, pagesize=letter)
    w, h = letter

    p.setFillColorRGB(0.05, 0.05, 0.10)
    p.rect(0, h - 100, w, 100, fill=1, stroke=0)
    p.setFillColorRGB(0, 0.95, 0.99)
    p.setFont("Helvetica-Bold", 22)
    p.drawCentredString(w / 2, h - 60, "ELITE AUCTIONS — PAYMENT RECEIPT")

    p.setFillColorRGB(0, 0, 0)
    p.setFont("Helvetica-Bold", 13)
    p.drawString(60, h - 140, "Transaction Details")
    p.setFont("Helvetica", 12)
    p.drawString(60, h - 165, f"Transaction ID : {payment.transaction_id}")
    p.drawString(60, h - 185, f"Item            : {payment.auction.title}")
    p.drawString(60, h - 205, f"Amount          : INR {payment.amount}")
    p.drawString(60, h - 225, f"Paid By         : {request.user.username}")
    p.drawString(60, h - 245, f"Status          : {payment.status}")
    p.drawString(60, h - 265, f"Date            : {payment.created_at.strftime('%d %b %Y, %H:%M')}")

    p.line(60, h - 280, w - 60, h - 280)
    p.setFont("Helvetica-Bold", 13)
    p.drawString(60, h - 300, "Delivery Address")
    p.setFont("Helvetica", 12)
    if order:
        p.drawString(60, h - 320, f"{order.delivery_address}, {order.city} - {order.pincode}")
        p.drawString(60, h - 340, f"Est. Delivery: {order.estimated_delivery}")
    else:
        p.drawString(60, h - 320, "Address: Not yet provided")

    p.showPage()
    p.save()
    return response


@login_required
def download_invoice(request, order_id):
    order = get_object_or_404(Order, id=order_id, winner=request.user)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Invoice_Order_{order.id}.pdf"'
    p = canvas.Canvas(response, pagesize=letter)
    w, h = letter

    p.setFillColorRGB(0.05, 0.05, 0.10)
    p.rect(0, h - 100, w, 100, fill=1, stroke=0)
    p.setFillColorRGB(0, 0.95, 0.99)
    p.setFont("Helvetica-Bold", 22)
    p.drawCentredString(w / 2, h - 60, "ELITE AUCTIONS — INVOICE")

    p.setFillColorRGB(0, 0, 0)
    p.setFont("Helvetica", 12)
    p.drawString(60, h - 140, f"Invoice #       : {order.id}")
    p.drawString(60, h - 160, f"Order Date      : {order.order_date.strftime('%d %b, %Y')}")
    p.drawString(60, h - 180, f"Item            : {order.auction.title}")
    p.drawString(60, h - 200, f"Amount Paid     : INR {order.auction.current_highest_bid}")
    p.drawString(60, h - 220, f"Buyer           : {request.user.username}")
    p.drawString(60, h - 240, f"Seller          : {order.auction.seller.username}")
    p.line(60, h - 258, w - 60, h - 258)
    p.setFont("Helvetica-Bold", 13)
    p.drawString(60, h - 275, "Shipping Address")
    p.setFont("Helvetica", 12)
    p.drawString(60, h - 295, f"{order.delivery_address}, {order.city} - {order.pincode}")
    p.drawString(60, h - 315, f"Status: {order.get_status_display()}")
    p.showPage()
    p.save()
    return response

# ─── DISPUTES ────────────────────────────────────────────────────────────────

@login_required
def raise_dispute(request, auction_id):
    auction = get_object_or_404(Auction, id=auction_id)
    if request.method == 'POST':
        form = DisputeForm(request.POST)
        if form.is_valid():
            dispute = form.save(commit=False)
            dispute.auction = auction
            dispute.complainant = request.user
            dispute.save()
            log_action(request.user, f'Raised dispute on auction {auction_id}', request)
            messages.success(request, "Dispute raised. Our team will review it shortly.")
            return redirect('my_bids')
    else:
        form = DisputeForm()
    return render(request, 'auctions/raise_dispute.html', {'auction': auction, 'form': form})


# ─── ADMIN DASHBOARD ─────────────────────────────────────────────────────────

class AdminDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'auctions/admin_dashboard.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return redirect('auction_list')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Bid velocity chart
        bid_data = (
            Bid.objects.annotate(date=TruncDate('timestamp'))
            .values('date').annotate(count=Count('id'))
            .order_by('date')[:30]
        )
        ctx['line_labels'] = json.dumps([b['date'].strftime("%b %d") for b in bid_data])
        ctx['line_values'] = json.dumps([b['count'] for b in bid_data])

        # Category breakdown
        cat_data = (
            Auction.objects.values('category__name')
            .annotate(count=Count('id'))
            .order_by('-count')[:8]
        )
        ctx['bar_labels'] = json.dumps([c['category__name'] or 'Uncategorised' for c in cat_data])
        ctx['bar_values'] = json.dumps([c['count'] for c in cat_data])

        ctx['total_revenue'] = (
            Auction.objects.filter(is_active=False)
            .aggregate(total=Sum('current_highest_bid'))['total'] or 0
        )
        ctx['active_disputes'] = Dispute.objects.filter(is_resolved=False).count()
        ctx['total_users'] = User.objects.count()
        ctx['active_auctions'] = Auction.objects.filter(is_active=True).count()
        ctx['total_bids'] = Bid.objects.count()
        ctx['pending_payments'] = Payment.objects.filter(status='PENDING').count()
        ctx['security_logs'] = SecurityLog.objects.select_related('user').order_by('-timestamp')[:10]
        ctx['recent_orders'] = Order.objects.select_related('winner', 'auction').order_by('-order_date')[:8]
        ctx['top_sellers'] = (
            Auction.objects.filter(is_active=False)
            .values('seller__username')
            .annotate(total=Sum('current_highest_bid'), count=Count('id'))
            .order_by('-total')[:5]
        )
        ctx['recent_bids'] = Bid.objects.select_related('bidder', 'auction').order_by('-timestamp')[:8]
        return ctx


@login_required
def admin_manage_table(request, model_name):
    if not request.user.is_staff:
        return redirect('auction_list')
    model_map = {
        'auctions': Auction, 'bids': Bid, 'categories': Category,
        'payments': Payment, 'users': User, 'disputes': Dispute,
        'security-logs': SecurityLog, 'orders': Order, 'reviews': Review,
    }
    selected_model = model_map.get(model_name)
    if not selected_model:
        return redirect('admin_dashboard')
    data = selected_model.objects.all().order_by('-id')
    context = {
        'data': data,
        'title': model_name.replace('-', ' ').title(),
        'model_name': model_name,
        'admin_model_name': selected_model._meta.model_name,
    }
    if model_name == 'orders':
        context['order_status_choices'] = Order.STATUS_CHOICES
    return render(request, 'auctions/admin_table_view.html', context)


@login_required
def admin_update_order_status(request, order_id):
    """Admin action: update order status"""
    if not request.user.is_staff or request.method != 'POST':
        return redirect('auction_list')
    
    order = get_object_or_404(Order, id=order_id)
    new_status = request.POST.get('status')
    
    if new_status in dict(Order.STATUS_CHOICES):
        order.status = new_status
        if new_status == 'DELIVERED':
            order.is_delivered = True
            # Release payment to seller
            if hasattr(order.auction, 'payment'):
                order.auction.payment.status = 'RELEASED'
                order.auction.payment.save()
            # Notify buyer
            notify(
                order.winner,
                f"Your order '{order.auction.title}' has been delivered! Please leave a review.",
                link=f"/review/leave/{order.auction.id}/",
            )
        else:
            order.is_delivered = False
            
        order.save()
        messages.success(request, f"Order #{order.id} status updated to {order.get_status_display()}.")
    else:
        messages.error(request, "Invalid status selected.")
        
    return redirect('admin_manage_table', model_name='orders')


@login_required
def generate_sales_report_admin(request):
    if not request.user.is_staff:
        return redirect('auction_list')

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="Elite_Auctions_Sales_Report.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("Elite Auctions — Sales Report", styles['Title']))
    elements.append(Spacer(1, 20))

    # Revenue summary
    total_rev = Auction.objects.filter(is_active=False).aggregate(t=Sum('current_highest_bid'))['t'] or 0
    elements.append(Paragraph(f"Total Platform Revenue: INR {total_rev}", styles['Heading2']))
    elements.append(Spacer(1, 10))

    # Table of sold auctions
    table_data = [['#', 'Item', 'Seller', 'Winner', 'Amount (INR)']]
    sold = Auction.objects.filter(is_active=False).exclude(winner__isnull=True).select_related('seller', 'winner')
    for i, a in enumerate(sold, 1):
        table_data.append([
            str(i), a.title[:40], a.seller.username,
            a.winner.username if a.winner else '—',
            str(a.current_highest_bid),
        ])

    t = Table(table_data, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1e2e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f4ff')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
    ]))
    elements.append(t)
    doc.build(elements)
    return response


def leaderboard_view(request):
    """Top Bidders Leaderboard with gamified stats & rankings"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    users = User.objects.annotate(
        total_bids=Count('bid', distinct=True),
        auctions_won=Count('won_auctions', distinct=True),
    ).filter(total_bids__gt=0).order_by('-auctions_won', '-total_bids')[:10]
    
    bidders_data = []
    for rank, u in enumerate(users, 1):
        spent = Auction.objects.filter(winner=u, is_active=False).aggregate(s=Sum('current_highest_bid'))['s'] or 0
        win_rate = round((u.auctions_won / u.total_bids * 100), 1) if u.total_bids > 0 else 0
        
        achievements = []
        if u.auctions_won >= 1:
            achievements.append({'icon': '🎯', 'name': 'First Win'})
        if spent >= 50000:
            achievements.append({'icon': '👑', 'name': 'High Roller'})
        if u.total_bids >= 5:
            achievements.append({'icon': '🔥', 'name': 'Active Bidder'})
        if u.vip_tier == 'Platinum':
            achievements.append({'icon': '💎', 'name': 'VIP Platinum'})
        elif u.vip_tier == 'Gold':
            achievements.append({'icon': '🏅', 'name': 'VIP Gold'})

        bidders_data.append({
            'rank': rank,
            'user': u,
            'total_bids': u.total_bids,
            'auctions_won': u.auctions_won,
            'total_spent': spent,
            'win_rate': win_rate,
            'achievements': achievements,
        })
        
    top_3 = bidders_data[:3]
    remaining = bidders_data[3:]
    
    context = {
        'top_3': top_3,
        'remaining': remaining,
        'all_bidders': bidders_data,
    }
    return render(request, 'auctions/leaderboard.html', context)

