import hashlib
import json
import razorpay
import uuid
from django.db.models.functions import TruncDate
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.contrib.auth import login
from django.db.models import Sum, Count, Max
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.http import HttpResponse
from django.contrib.auth.views import LoginView
from django.core.mail import send_mail
from django.conf import settings

# ReportLab Imports
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

# Local Imports
from .models import Auction, Bid, Category, SecurityLog, Payment, Dispute, User
from .forms import (
    CustomUserCreationForm, 
    AuctionListingForm, 
    UserProfileForm, 
    EmailLoginForm
)

# --- AUTOMATION ---
def finalize_expired_auctions():
    expired_auctions = Auction.objects.filter(is_active=True, end_time__lt=timezone.now())
    for auction in expired_auctions:
        highest_bid = Bid.objects.filter(auction=auction).order_by('-amount').first()
        if highest_bid:
            auction.winner = highest_bid.bidder
            auction.current_highest_bid = highest_bid.amount
            transaction_data = f"{auction.id}-{auction.winner.id}-{auction.current_highest_bid}"
            auction.transaction_hash = hashlib.sha256(transaction_data.encode()).hexdigest()
        auction.is_active = False
        auction.save()

# --- AUTH & REDIRECTS ---

@login_required
def login_redirect(request):
    """
    The Gatekeeper: Directs Admins/Staff to the Dashboard 
    and normal users to the Shop Listings.
    """
    if request.user.is_staff or request.user.is_superuser:
        return redirect('admin_dashboard')
    return redirect('auction_list')

class CustomLoginView(LoginView):
    authentication_form = EmailLoginForm
    template_name = 'registration/login.html'

    def get_success_url(self):
        # Always send to our gatekeeper function to ensure logic consistency
        return reverse('login_redirect')

    def form_valid(self, form):
        response = super().form_valid(form)
        SecurityLog.objects.create(
            user=self.request.user, 
            action="Successful Login", 
            ip_address=self.request.META.get('REMOTE_ADDR')
        )
        return response

def register_view(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome, {user.username}!")
            return redirect('login_redirect')
    else:
        form = CustomUserCreationForm()
    return render(request, "registration/register.html", {"form": form})

@login_required
def edit_profile(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('auction_list')
    else:
        form = UserProfileForm(instance=request.user)
    return render(request, 'registration/edit_profile.html', {'form': form})

# --- AUCTION VIEWS ---
def auction_list(request):
    auctions = Auction.objects.filter(is_active=True)
    categories = Category.objects.all()

    query = request.GET.get('q')
    category_id = request.GET.get('category')

    if query:
        auctions = auctions.filter(
            Q(title__icontains=query) | 
            Q(description__icontains=query)
        )

    if category_id:
        auctions = auctions.filter(category_id=category_id)

    return render(request, 'auctions/list.html', {
        'auctions': auctions,
        'categories': categories,
    })

@login_required
def auction_detail(request, auction_id):
    auction = get_object_or_404(Auction, id=auction_id)
    bids_for_chart = auction.bids.all().order_by('timestamp')
    
    chart_labels = [bid.timestamp.strftime("%H:%M") for bid in bids_for_chart]
    chart_data = [float(bid.amount) for bid in bids_for_chart]

    return render(request, 'auctions/detail.html', {
        'auction': auction,
        'bids': bids_for_chart.order_by('-amount'), 
        'chart_labels': json.dumps(chart_labels),   
        'chart_data': json.dumps(chart_data),       
    })

@login_required
def place_bid(request, auction_id):
    auction = get_object_or_404(Auction, id=auction_id)
    if request.method == "POST":
        bid_amount = float(request.POST.get('bid_amount'))
        if bid_amount > float(auction.current_highest_bid):
            Bid.objects.create(auction=auction, bidder=request.user, amount=bid_amount)
            auction.current_highest_bid = bid_amount
            auction.save()
            messages.success(request, "Bid placed!")
    return redirect('auction_detail', auction_id=auction.id)

@login_required
def my_bids(request):
    bid_ids = Bid.objects.filter(bidder=request.user).values_list('auction_id', flat=True).distinct()
    auctions = Auction.objects.filter(id__in=bid_ids).order_by('-is_active')
    return render(request, 'auctions/my_bids.html', {'auctions': auctions})

# --- ADMIN & DASHBOARD ---
class AdminDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'auctions/admin_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        bid_data = Bid.objects.annotate(date=TruncDate('timestamp')) \
                             .values('date') \
                             .annotate(count=Count('id')) \
                             .order_by('date')[:7]
        
        line_labels = [b['date'].strftime("%b %d") for b in bid_data]
        line_values = [b['count'] for b in bid_data]

        cat_data = Category.objects.annotate(num_auctions=Count('items')) \
                                   .values('name', 'num_auctions')
        
        context['line_labels'] = json.dumps(line_labels)
        context['line_values'] = json.dumps(line_values)
        context['bar_labels'] = json.dumps([c['name'] for c in cat_data])
        context['bar_values'] = json.dumps([c['num_auctions'] for c in cat_data])
        
        context['total_revenue'] = Auction.objects.filter(is_active=False).aggregate(total=Sum('current_highest_bid'))['total'] or 0
        context['active_disputes'] = Dispute.objects.filter(is_resolved=False).count()
        context['total_users'] = User.objects.count()
        context['security_logs'] = SecurityLog.objects.all().order_by('-timestamp')[:8]
        
        return context

# --- PAYMENT & REPORTS ---
@login_required
def checkout(request, auction_id):
    auction = get_object_or_404(Auction, id=auction_id)
    amount_in_paise = int(auction.current_highest_bid * 100)
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    data = {
        "amount": amount_in_paise,
        "currency": "INR",
        "receipt": f"auction_{auction.id}",
        "payment_capture": 1
    }
    razorpay_order = client.order.create(data=data)

    return render(request, 'auctions/checkout.html', {
        'auction': auction,
        'razorpay_order_id': razorpay_order['id'],
        'razorpay_key': settings.RAZORPAY_KEY_ID,
        'amount': amount_in_paise,
    })

@login_required
def payment_success(request, payment_id):
    auction = get_object_or_404(Auction, id=payment_id) 
    razor_pay_id = request.GET.get('pay_id')

    payment, created = Payment.objects.get_or_create(
        auction=auction,
        defaults={
            'amount': auction.current_highest_bid,
            'transaction_id': razor_pay_id,
            'status': 'COMPLETED'
        }
    )

    return render(request, 'auctions/payment_success.html', {
        'payment': payment,
        'auction': auction
    })

@login_required
def generate_sales_report(request):
    if not request.user.is_staff: return redirect('auction_list')
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="Sales_Report.pdf"'
    doc = SimpleDocTemplate(response, pagesize=letter)
    elements = [Paragraph("Elite Auctions - Sales Report", getSampleStyleSheet()['Title'])]
    doc.build(elements)
    return response

@login_required
def download_receipt(request, payment_id):
    payment = get_object_or_404(Payment, id=payment_id)
    if payment.auction.winner != request.user and not request.user.is_staff:
        messages.error(request, "Unauthorized access.")
        return redirect('my_bids')

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Receipt_{payment.transaction_id}.pdf"'

    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter
    p.setFont("Helvetica-Bold", 24)
    p.drawCentredString(width / 2, 750, "ELITE AUCTIONS")
    p.setFont("Helvetica", 12)
    p.drawString(50, 660, f"Receipt ID: {payment.transaction_id}")
    p.drawString(50, 640, f"Date: {payment.created_at.strftime('%B %d, %Y')}")
    p.drawString(50, 620, f"Customer: {request.user.get_full_name()} (@{request.user.username})")
    p.line(50, 600, 550, 600)
    p.drawString(60, 545, f"Item: {payment.auction.title}")
    p.drawRightString(540, 545, f"Total Paid: ${payment.amount}")
    p.showPage()
    p.save()
    return response

@login_required
def raise_dispute(request, auction_id):
    auction = get_object_or_404(Auction, id=auction_id)
    if request.method == "POST":
        Dispute.objects.create(
            auction=auction, 
            complainant=request.user, 
            reason=request.POST.get('reason')
        )
        messages.success(request, "Dispute raised successfully.")
        return redirect('my_bids')
    return render(request, 'auctions/raise_dispute.html', {'auction': auction})

# Add this to your existing views.py
@login_required
def admin_manage_table(request, model_name):
    """
    Dynamically fetches data for the sidebar links (Auctions, Users, etc.)
    and displays them inside the Custom Dashboard theme.
    """
    if not request.user.is_staff:
        return redirect('auction_list')

    # Mapping string names to actual Models
    model_map = {
        'auctions': Auction,
        'bids': Bid,
        'categories': Category,
        'payments': Payment,
        'users': User,
        'disputes': Dispute,
        'security-logs': SecurityLog,
    }

    selected_model = model_map.get(model_name)
    if not selected_model:
        return redirect('admin_dashboard')

    data = selected_model.objects.all().order_by('-id')
    
    return render(request, 'auctions/admin_table_view.html', {
        'data': data,
        'title': model_name.replace('-', ' ').title(),
        'model_name': model_name
    })