from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.safestring import mark_safe
from .models import User, Auction, Category, Bid, Payment, SecurityLog, Dispute

# --- THE ULTIMATE ELITE UI INJECTION ---
ADMIN_STYLE = """
<style>
    /* Global Background & Fonts */
    body, #content { background-color: #0b0d14 !important; color: #e6edf3 !important; font-family: 'Segoe UI', Roboto, sans-serif !important; }
    
    /* Header & Top Navigation */
    #header { background: #161a26 !important; border-bottom: 3px solid #00f2fe !important; padding: 15px 40px !important; }
    #branding h1 { color: #00f2fe !important; font-weight: 800 !important; text-transform: uppercase; letter-spacing: 2px; font-size: 24px !important; }
    #user-tools { color: #8b949e !important; font-weight: 600; }
    #user-tools a { color: #00f2fe !important; }
    
    /* Breadcrumbs & Module Titles */
    .breadcrumbs { background: #1c212e !important; color: #8b949e !important; border-bottom: 1px solid #2d333b !important; padding: 12px 40px !important; }
    .breadcrumbs a { color: #4facfe !important; font-weight: bold; }
    .module h2, .module caption { background: #1c212e !important; color: #00f2fe !important; font-weight: 700 !important; text-transform: uppercase; letter-spacing: 1px; }
    
    /* Table Styling (List Views) */
    .results table { border-radius: 12px !important; overflow: hidden !important; border: 1px solid #2d333b !important; }
    thead th { background: #1c212e !important; color: #8b949e !important; border-bottom: 2px solid #2d333b !important; text-transform: uppercase; font-size: 11px; }
    tr.row1 { background: #161a26 !important; }
    tr.row2 { background: #1c212e !important; }
    tr:hover { background: rgba(0, 242, 254, 0.08) !important; transition: 0.2s; }
    
    /* Form & Input Styling (Add/Edit Views) */
    fieldset { background: #161a26 !important; border: 1px solid #2d333b !important; border-radius: 12px !important; padding: 20px !important; margin-bottom: 20px !important; }
    .form-row { border-bottom: 1px solid #2d333b !important; padding: 15px !important; }
    input[type=text], input[type=password], input[type=email], input[type=number], textarea, select {
        background: #0b0d14 !important; border: 1px solid #2d333b !important; color: #fff !important; 
        border-radius: 6px !important; padding: 10px !important; width: 100%;
    }
    input:focus, textarea:focus { border-color: #00f2fe !important; box-shadow: 0 0 8px rgba(0, 242, 254, 0.3) !important; outline: none; }
    
    /* Buttons (The Glow Effect) */
    .button, input[type=submit], .default { 
        background: linear-gradient(135deg, #00f2fe 0%, #4facfe 100%) !important; 
        color: #000 !important; font-weight: 800 !important; border: none !important; 
        border-radius: 8px !important; padding: 12px 25px !important; text-transform: uppercase; cursor: pointer;
    }
    .button:hover, input[type=submit]:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0, 242, 254, 0.4); transition: 0.3s; }
    .submit-row { background: #1c212e !important; border: 1px solid #2d333b !important; border-radius: 12px; padding: 20px; }

    /* Filters Sidebar */
    #changelist-filter { background: #161a26 !important; border-left: 1px solid #2d333b !important; }
    #changelist-filter h2 { background: #00f2fe !important; color: #000 !important; }
    #changelist-filter li.selected a { color: #00f2fe !important; border-left-color: #00f2fe !important; }

    /* Search Bar */
    #searchbar { background: #1c212e !important; border: 1px solid #00f2fe !important; color: #fff !important; border-radius: 20px !important; padding: 8px 20px !important; }
    
    /* Icons Fix */
    .related-widget-wrapper-link img { filter: invert(1) hue-rotate(180deg) brightness(1.5); }
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
            
        winner = obj.auto_winner
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