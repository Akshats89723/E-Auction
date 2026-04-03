from django.urls import path
from . import views

urlpatterns = [
    # --- Home & Listings ---
    path('', views.auction_list, name='auction_list'),
    path('listings/', views.auction_list, name='auction_list_alias'), 
    path('auction/<int:auction_id>/', views.auction_detail, name='auction_detail'),
    
    # --- The Gatekeeper ---
    path('login-redirect/', views.login_redirect, name='login_redirect'),
    
    # --- User Authentication & Profile ---
    path('accounts/login/', views.CustomLoginView.as_view(), name='login'),
    path('register/', views.register_view, name='register'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    
    # --- Bidding & User Activity ---
    path('bid/<int:auction_id>/', views.place_bid, name='place_bid'),
    path('my-bids/', views.my_bids, name='my_bids'),
    
    # --- Payments & Receipts ---
    path('checkout/<int:auction_id>/', views.checkout, name='checkout'),
    path('payment-success/<int:payment_id>/', views.payment_success, name='payment_success'),
    path('receipt/<int:payment_id>/', views.download_receipt, name='download_receipt'),
    
    # --- Admin & Analytics (Your Custom Dashboard) ---
    path('admin-dashboard/', views.AdminDashboardView.as_view(), name='admin_dashboard'),
    path('admin-dashboard/sales-report/', views.generate_sales_report, name='generate_sales_report'),
    path('admin-dashboard/manage/<str:model_name>/', views.admin_manage_table, name='admin_manage_table'),
    
    # --- Disputes ---
    path('dispute/<int:auction_id>/', views.raise_dispute, name='raise_dispute'),
]











