from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    # --- Home & Listings ---
    path('', views.auction_list, name='auction_list'),
    path('listings/', views.auction_list, name='auction_list_alias'),
    path('leaderboard/', views.leaderboard_view, name='leaderboard'),
    path('auction/<int:auction_id>/', views.auction_detail, name='auction_detail'),
    path('auction/create/', views.create_auction, name='create_auction'),

    # --- Draft Management ---
    path('my-drafts/', views.my_drafts, name='my_drafts'),
    path('auction/<int:auction_id>/publish/', views.publish_draft, name='publish_draft'),

    # --- Gatekeeper ---
    path('login-redirect/', views.login_redirect, name='login_redirect'),

    # --- Auth & Profile ---
    path('accounts/login/', views.CustomLoginView.as_view(), name='login'),
    path('register/', views.register_view, name='register'),
    path('verify-email/<str:token>/', views.verify_email, name='verify_email'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('seller/<int:user_id>/', views.seller_profile, name='seller_profile'),

    # --- Live Bid API ---
    path('api/auction/<int:auction_id>/latest-bid/', views.get_latest_bid, name='get_latest_bid'),

    # --- Bidding ---
    path('bid/<int:auction_id>/', views.place_bid, name='place_bid'),
    path('auto-bid/<int:auction_id>/', views.set_auto_bid, name='set_auto_bid'),
    path('auto-bid/<int:auction_id>/cancel/', views.cancel_auto_bid, name='cancel_auto_bid'),

    # --- User Activity ---
    path('my-bids/', views.my_bids, name='my_bids'),
    path('my-orders/', views.my_orders, name='my_orders'),
    path('sold-items/', views.sold_items_view, name='sold_items'),

    # --- Watchlist & Notifications ---
    path('watchlist/toggle/<int:auction_id>/', views.toggle_watchlist, name='toggle_watchlist'),
    path('my-watchlist/', views.my_watchlist, name='my_watchlist'),
    path('notifications/', views.notifications_view, name='notifications'),

    # --- Reviews ---
    path('review/leave/<int:auction_id>/', views.leave_review, name='leave_review'),

    # --- Payments ---
    path('checkout/<int:auction_id>/', views.checkout, name='checkout'),
    path('create-order/<int:auction_id>/', views.create_order, name='create_order'),
    path('payment-success/<int:auction_id>/', views.payment_success, name='payment_success'),
    path('receipt/<int:payment_id>/', views.download_receipt, name='download_receipt'),
    path('invoice/<int:order_id>/', views.download_invoice, name='download_invoice'),

    # --- Admin Dashboard ---
    path('admin-dashboard/', views.AdminDashboardView.as_view(), name='admin_dashboard'),
    path('admin-dashboard/sales-report/', views.generate_sales_report_admin, name='generate_sales_report'),
    path('admin-dashboard/manage/<str:model_name>/', views.admin_manage_table, name='admin_manage_table'),
    path('admin-dashboard/order/<int:order_id>/update-status/', views.admin_update_order_status, name='admin_update_order_status'),

    # --- Disputes ---
    path('dispute/<int:auction_id>/', views.raise_dispute, name='raise_dispute'),

    # --- Password Reset ---
    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='registration/password_reset_form.html'), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='registration/password_reset_complete.html'), name='password_reset_complete'),
]





