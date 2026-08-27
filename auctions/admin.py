from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.utils.html import format_html
from .models import User, Auction, AuctionImage, AutoBid, Category, Bid, Payment, SecurityLog, Dispute, Order, Review, Watchlist, Notification

# --- THE ULTIMATE ELITE UI INJECTION ---
ADMIN_STYLE = """
<style>
    /* Force Django Admin CSS Variables to our Neon Synthwave Theme */
    :root, html[data-theme="light"], html[data-theme="dark"] {
        --primary: #b500ff !important;
        --secondary: #00e5ff !important;
        --accent: #ff00a0 !important;
        --primary-fg: #ffffff !important;
        
        --body-bg: #0a0614 !important;
        --body-fg: #f5edff !important;
        --body-quiet-color: #a494cc !important;
        --body-loud-color: #ffffff !important;
        
        --header-color: #00e5ff !important;
        --header-branding-color: #00e5ff !important;
        --header-bg: #100c1e !important;
        --header-link-color: #a494cc !important;
        
        --breadcrumbs-fg: #a494cc !important;
        --breadcrumbs-link-fg: #00e5ff !important;
        --breadcrumbs-bg: #1b1236 !important;
        
        --link-fg: #00e5ff !important;
        --link-hover-color: #ff00a0 !important;
        --link-selected-fg: #ff00a0 !important;
        
        --hairline-color: #2a1b4d !important;
        --border-color: #2a1b4d !important;
        
        --error-fg: #ff0055 !important;
        --message-success-bg: rgba(0, 255, 102, 0.1) !important;
        
        --darkened-bg: #100c1e !important;
        --selected-bg: rgba(181, 0, 255, 0.15) !important;
        --selected-row: rgba(0, 229, 255, 0.1) !important;
        
        --button-fg: #ffffff !important;
        --button-bg: #b500ff !important;
        --button-hover-bg: #ff00a0 !important;
        --default-button-bg: #b500ff !important;
        --default-button-hover-bg: #ff00a0 !important;
        
        --object-tools-fg: #ffffff !important;
        --object-tools-bg: #1b1236 !important;
        --object-tools-hover-bg: #b500ff !important;
    }

    /* Global Background & Fonts */
    body, #content, .toggle-nav-sidebar { background-color: var(--body-bg) !important; color: var(--body-fg) !important; font-family: 'Segoe UI', Roboto, sans-serif !important; }
    
    /* Header & Top Navigation */
    #header { background: var(--header-bg) !important; border-bottom: 3px solid var(--primary) !important; padding: 15px 40px !important; }
    #branding h1 { color: var(--primary) !important; font-weight: 800 !important; text-transform: uppercase; letter-spacing: 2px; font-size: 24px !important; }
    #user-tools { color: var(--body-quiet-color) !important; font-weight: 600; }
    #user-tools a { color: var(--primary) !important; }
    
    /* Nav Sidebar */
    #nav-sidebar { background-color: var(--darkened-bg) !important; border-right: 1px solid var(--border-color) !important; }
    #nav-sidebar th, #nav-sidebar td { border-bottom: 1px solid var(--border-color) !important; background: transparent !important; }
    #nav-sidebar a { color: var(--body-quiet-color) !important; }
    #nav-sidebar a:hover { color: var(--primary) !important; background-color: var(--selected-bg) !important; }
    #nav-sidebar tr.current-app .section:link { color: var(--primary) !important; }
    #nav-sidebar tr.current-model { background-color: var(--selected-bg) !important; }
    #nav-sidebar tr.current-model a { color: var(--primary) !important; font-weight: bold; }
    .toggle-nav-sidebar::before { filter: invert(1); }

    /* Breadcrumbs & Module Titles */
    .breadcrumbs { background: #1c212e !important; color: #8b949e !important; border-bottom: 1px solid #2d333b !important; padding: 12px 40px !important; }
    .breadcrumbs a { color: #4facfe !important; font-weight: bold; }
    .module h2, .module caption, inline-group h2 { background: #1c212e !important; color: #00f2fe !important; font-weight: 700 !important; text-transform: uppercase; letter-spacing: 1px; }
    
    /* Table Styling (List Views) */
    .results table { border-radius: 12px !important; overflow: hidden !important; border: 1px solid #2d333b !important; }
    thead th { background: #1c212e !important; color: #8b949e !important; border-bottom: 2px solid #2d333b !important; text-transform: uppercase; font-size: 11px; }
    tr.row1 { background: #161a26 !important; }
    tr.row2 { background: #1c212e !important; }
    tr:hover { background: rgba(0, 242, 254, 0.08) !important; transition: 0.2s; }
    td, th { color: #e6edf3 !important; }
    .results a { color: #4facfe !important; }
    
    /* Form & Input Styling (Add/Edit Views) */
    fieldset { background: #161a26 !important; border: 1px solid #2d333b !important; border-radius: 12px !important; padding: 20px !important; margin-bottom: 20px !important; }
    .form-row { border-bottom: 1px solid #2d333b !important; padding: 15px !important; }
    label, .aligned label { color: #8b949e !important; font-weight: bold !important; }
    input[type=text], input[type=password], input[type=email], input[type=number], input[type=url], textarea, select, .vTextField, .vLargeTextField {
        background: #0b0d14 !important; border: 1px solid #2d333b !important; color: #fff !important; 
        border-radius: 6px !important; padding: 8px 12px !important; max-width: 100%;
        box-sizing: border-box !important; height: auto !important; font-size: 14px !important;
    }
    input:focus, textarea:focus, select:focus { border-color: #00f2fe !important; box-shadow: 0 0 8px rgba(0, 242, 254, 0.3) !important; outline: none; }
    .help, .help-tooltip { color: #64748b !important; }
    .readonly { color: #00f2fe !important; font-weight: bold; }
    
    /* Select2 (Foreign Key dropdowns) */
    .select2-container .select2-selection--single, .select2-container .select2-selection--multiple { background-color: #0b0d14 !important; border-color: #2d333b !important; min-height: 38px !important; }
    .select2-container .select2-selection__rendered, .select2-container .select2-selection__rendered * { color: #fff !important; line-height: 38px !important; }
    .select2-dropdown { background-color: #161a26 !important; border: 1px solid #2d333b !important; }
    .select2-results__option { color: #e6edf3 !important; }
    .select2-container--default .select2-results__option--highlighted[aria-selected] { background-color: #00f2fe !important; color: #000 !important; }
    .select2-search input { background-color: #0b0d14 !important; color: #fff !important; border: 1px solid #2d333b !important; }
    
    /* Object Tools (History Button, etc) */
    .object-tools a { background: #1c212e !important; color: #00f2fe !important; border: 1px solid #2d333b !important; border-radius: 20px !important; padding: 8px 15px !important; text-transform: uppercase; font-size: 11px !important; font-weight: bold; }
    .object-tools a:hover { background: #00f2fe !important; color: #0b0d14 !important; box-shadow: 0 0 10px rgba(0, 242, 254, 0.4); }

    /* Buttons (The Glow Effect) */
    .button, input[type=submit], .default { 
        background: linear-gradient(135deg, var(--primary) 0%, var(--accent) 100%) !important; 
        color: #fff !important; font-weight: 900 !important; border: none !important; 
        border-radius: 8px !important; padding: 12px 25px !important; text-transform: uppercase; cursor: pointer;
    }
    .button:hover, input[type=submit]:hover { transform: translateY(-3px) scale(1.02); box-shadow: 0 8px 25px rgba(255, 0, 160, 0.6); transition: 0.3s; }
    .submit-row { background: #1c212e !important; border: 1px solid #2d333b !important; border-radius: 12px; padding: 20px; }
    .submit-row a.deletelink { color: #ff4444 !important; font-weight: bold; }

    /* Action Bar Fixes */
    .actions { display: flex !important; align-items: center !important; gap: 15px; padding: 15px !important; background: var(--header-bg) !important; border-radius: 8px; margin-bottom: 15px; border: 1px solid var(--border-color); }
    .actions label { margin: 0 !important; display: flex !important; align-items: center !important; gap: 10px; }
    .actions select { margin: 0 !important; height: 38px !important; }
    .actions .button { padding: 0 20px !important; margin: 0 !important; height: 38px !important; display: flex !important; align-items: center !important; justify-content: center !important; font-size: 13px !important; }
    .actions .action-counter { color: var(--body-quiet-color) !important; font-weight: bold; }

    /* Filters Sidebar */
    #changelist-filter { background: #161a26 !important; border-left: 1px solid #2d333b !important; }
    #changelist-filter h2 { background: linear-gradient(90deg, var(--primary), var(--secondary)) !important; color: #fff !important; font-weight: 900; letter-spacing: 1px; text-transform: uppercase; }
    #changelist-filter a { color: #8b949e !important; }
    #changelist-filter li.selected a { color: #00f2fe !important; border-left-color: #00f2fe !important; }
    #changelist-filter a:hover { color: #00f2fe !important; }

    /* Search Bar */
    #searchbar { background: var(--header-bg) !important; border: 1px solid var(--secondary) !important; color: #fff !important; border-radius: 20px !important; padding: 8px 20px !important; box-shadow: inset 0 0 10px rgba(0, 229, 255, 0.1); }
    #searchbar:focus { box-shadow: 0 0 15px rgba(0, 229, 255, 0.5) !important; outline: none; }
    
    /* Messages */
    ul.messagelist li.success { background: rgba(0, 255, 0, 0.1) !important; color: #00ff00 !important; border: 1px solid #00ff00 !important; border-radius: 8px !important; }
    ul.messagelist li.warning { background: rgba(255, 204, 0, 0.1) !important; color: #ffcc00 !important; border: 1px solid #ffcc00 !important; border-radius: 8px !important; }
    ul.messagelist li.error { background: rgba(255, 68, 68, 0.1) !important; color: #ff4444 !important; border: 1px solid #ff4444 !important; border-radius: 8px !important; }

    /* Icons Fix */
    .related-widget-wrapper-link img { filter: invert(1) hue-rotate(180deg) brightness(1.5); }
    .selector-chooseall, .selector-clearall { color: #00f2fe !important; }
</style>
"""

# Apply Global Branding
admin.site.site_header = mark_safe(ADMIN_STYLE + 'ELITE COMMAND CENTER')
admin.site.site_title = "Elite Auctions Portal"
admin.site.index_title = "Platform Management Hub"

# --- Custom User Admin ---
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Elite Profile', {'fields': ('profile_photo', 'is_premium', 'is_buyer', 'is_seller', 'phone_number')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Elite Profile', {'fields': ('profile_photo', 'is_premium', 'is_buyer', 'is_seller', 'phone_number')}),
    )
    list_display = ('username', 'email', 'status_badge', 'premium_tag', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'is_premium')
    search_fields = ('username', 'email')

    def status_badge(self, obj):
        color = "#00ff00" if obj.is_active else "#ff4444"
        text = "● ACTIVE" if obj.is_active else "○ BANNED"
        return mark_safe(f'<b style="color: {color}; font-size: 11px; letter-spacing: 1px;">{text}</b>')
    status_badge.short_description = "Status"
    
    def premium_tag(self, obj):
        if obj.is_premium:
            return mark_safe('<span style="background: linear-gradient(90deg, #00f2fe, #4facfe); color: black; padding: 3px 10px; border-radius: 12px; font-weight: 800; font-size: 10px;">PREMIUM</span>')
        return mark_safe('<span style="color: #666;">Standard</span>')
    premium_tag.short_description = "Tier"

# --- Auction Management ---
@admin.register(Auction)
class AuctionAdmin(admin.ModelAdmin):
    list_display = ('title', 'seller', 'styled_price', 'end_time', 'display_winner', 'is_active')
    list_filter = ('is_active', 'category', 'start_time')
    search_fields = ('title', 'description', 'seller__email')
    readonly_fields = ('current_highest_bid','display_winner')
    exclude = ('winner',)


    def display_winner(self, obj):
        # Ensure 'obj' exists and has a primary key (not a new 'Add' form)
        if not obj.pk or not obj.end_time:
            return mark_safe('<span style="color: #8b949e;">Waiting for data...</span>')
            
        winner = obj.winner
        if obj.is_finished:
            if winner:
                return mark_safe(f'<span style="color: #00f2fe; font-weight: bold;">🏆 {winner.username}</span>')
            return mark_safe('<span style="color: #8b949e;">No Bids</span>')
        
        return mark_safe('<span style="color: #ffcc00;">In Progress...</span>')
    
    display_winner.short_description = "Calculated Winner"



    def styled_price(self, obj):
        return mark_safe(f'<b style="color: #00f2fe; font-size: 1.1em; font-family: monospace;">₹{obj.current_highest_bid}</b>')
    styled_price.short_description = "Current Bid"

# --- Financials & Payments ---
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'auction', 'amount_display', 'status_tag', 'created_at')
    list_filter = ('status', 'created_at')
    
    def amount_display(self, obj):
        return mark_safe(f'<span style="color: #00ff00; font-family: monospace; font-weight: bold;">₹{obj.amount}</span>')

    def status_tag(self, obj):
        colors = {'completed': '#00ff00', 'pending': '#ffcc00', 'failed': '#ff4444'}
        color = colors.get(obj.status.lower(), '#ffffff')
        return mark_safe(f'<span style="border: 1px solid {color}; color: {color}; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 10px;">{obj.status.upper()}</span>')

@admin.register(Bid)
class BidAdmin(admin.ModelAdmin):
    list_display = ('auction', 'bidder', 'amount', 'timestamp')
    list_filter = ('timestamp',)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(Dispute)
class DisputeAdmin(admin.ModelAdmin):
    list_display = ('auction', 'complainant', 'resolution_status', 'timestamp')
    list_filter = ('is_resolved',)
    
    def resolution_status(self, obj):
        if obj.is_resolved:
            return mark_safe('<span style="color: #00f2fe; font-weight: bold;">✔ RESOLVED</span>')
        return mark_safe('<span style="color: #ff4444; font-weight: bold;">✘ PENDING</span>')

@admin.register(SecurityLog)
class SecurityLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'ip_address', 'threat_level', 'timestamp')
    list_filter = ('is_suspicious', 'timestamp')
    readonly_fields = ('user', 'action', 'ip_address', 'timestamp')

    def threat_level(self, obj):
        if obj.is_suspicious:
            return mark_safe('<span style="background: #ff4444; color: white; padding: 3px 8px; border-radius: 4px; font-weight: 900; font-size: 10px;">HIGH THREAT</span>')
        return mark_safe('<span style="color: #00ff00;">Safe</span>')


# ─── Additional Admin Registrations ─────────────────────────────────────────

class AuctionImageInline(admin.TabularInline):
    model = AuctionImage
    extra = 1
    fields = ('image', 'caption', 'order')


# Add inline images to AuctionAdmin
AuctionAdmin.inlines = [AuctionImageInline]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'auction', 'winner', 'city', 'status_badge', 'order_date')
    list_filter = ('status', 'is_delivered', 'order_date')
    search_fields = ('winner__email', 'auction__title')
    readonly_fields = ('order_date', 'estimated_delivery')
    actions = ['mark_as_delivered']

    def status_badge(self, obj):
        colors_map = {
            'PROCESSING': '#ffcc00', 'SHIPPED': '#4facfe',
            'OUT_FOR_DELIVERY': '#00f2fe', 'DELIVERED': '#00ff00', 'CANCELLED': '#ff4444',
        }
        c = colors_map.get(obj.status, '#ffffff')
        return mark_safe(f'<span style="color:{c};font-weight:700;">{obj.get_status_display()}</span>')
    status_badge.short_description = "Status"


    @admin.action(description='Mark selected orders as delivered')
    def mark_as_delivered(self, request, queryset):
        queryset.update(status='DELIVERED', is_delivered=True)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('reviewer', 'reviewee', 'rating', 'created_at')
    list_filter = ('rating',)
    search_fields = ('reviewer__username', 'reviewee__username')


@admin.register(AutoBid)
class AutoBidAdmin(admin.ModelAdmin):
    list_display = ('bidder', 'auction', 'max_amount', 'is_active', 'created_at')
    list_filter = ('is_active',)


@admin.register(Watchlist)
class WatchlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'auction', 'added_at')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'message_short', 'is_read', 'timestamp')
    list_filter = ('is_read',)

    def message_short(self, obj):
        return obj.message[:60]
    message_short.short_description = "Message"
