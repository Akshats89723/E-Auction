import datetime
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from auctions.models import User, Category, Auction, Bid, AutoBid, Watchlist, Notification, Order, Payment

class Command(BaseCommand):
    help = 'Seed the database with sample categories, demo users, auctions, and bid history.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Starting database seeding..."))

        # 1. Categories
        categories_data = [
            ("Electronics", "bi-laptop"),
            ("Luxury Watches", "bi-watch"),
            ("Fine Art", "bi-palette"),
            ("Collectibles", "bi-gem"),
            ("Supercars & Bikes", "bi-car-front"),
            ("Fashion & Jewelry", "bi-bag-heart"),
        ]

        categories = {}
        for name, icon in categories_data:
            cat, created = Category.objects.get_or_create(name=name, defaults={'icon': icon})
            categories[name] = cat
            if created:
                self.stdout.write(self.style.SUCCESS(f"  Created Category: {name}"))

        # 2. Demo Users
        users_info = [
            {
                'username': 'admin',
                'email': 'admin@example.com',
                'password': 'Password123!',
                'is_staff': True,
                'is_superuser': True,
                'is_admin': True,
                'xp': 10000,
                'bio': 'System Administrator & Head of Elite Auctions.',
            },
            {
                'username': 'seller',
                'email': 'seller@example.com',
                'password': 'Password123!',
                'is_seller': True,
                'is_premium': True,
                'xp': 5500,  # Platinum VIP
                'bio': 'Verified collector and luxury goods reseller.',
            },
            {
                'username': 'buyer1',
                'email': 'buyer1@example.com',
                'password': 'Password123!',
                'is_buyer': True,
                'xp': 2200,  # Gold VIP
                'bio': 'Art lover and watch enthusiast.',
            },
            {
                'username': 'buyer2',
                'email': 'buyer2@example.com',
                'password': 'Password123!',
                'is_buyer': True,
                'xp': 700,  # Silver VIP
                'bio': 'Tech collector & bidder.',
            },
        ]

        users = {}
        for udata in users_info:
            email = udata['email']
            user = User.objects.filter(email=email).first()
            if not user:
                user = User.objects.create_user(
                    username=udata['username'],
                    email=email,
                    password=udata['password'],
                    is_buyer=udata.get('is_buyer', False),
                    is_seller=udata.get('is_seller', False),
                    is_staff=udata.get('is_staff', False),
                    is_superuser=udata.get('is_superuser', False),
                    is_admin=udata.get('is_admin', False),
                    is_premium=udata.get('is_premium', False),
                    xp=udata.get('xp', 0),
                    bio=udata.get('bio', ''),
                    email_verified=True,
                    is_active=True,
                )
                self.stdout.write(self.style.SUCCESS(f"  Created User: {user.username} ({user.email})"))
            else:
                user.is_active = True
                user.email_verified = True
                user.save()
            users[udata['username']] = user

        seller = users['seller']
        buyer1 = users['buyer1']
        buyer2 = users['buyer2']

        # 3. Auctions
        now = timezone.now()
        auctions_data = [
            {
                'title': 'MacBook Pro M3 Max 16-inch (Space Black)',
                'description': 'Brand new sealed 16-inch M3 Max MacBook Pro, 36GB RAM, 1TB SSD. Full Apple warranty included.',
                'category': categories['Electronics'],
                'starting_bid': Decimal('150000.00'),
                'reserve_price': Decimal('175000.00'),
                'buy_now_price': Decimal('220000.00'),
                'min_bid_increment': Decimal('5000.00'),
                'end_time': now + datetime.timedelta(days=4),
                'bids': [
                    (buyer2, Decimal('155000.00')),
                    (buyer1, Decimal('160000.00')),
                    (buyer2, Decimal('165000.00')),
                    (buyer1, Decimal('170000.00')),
                ]
            },
            {
                'title': 'Rolex Submariner Date 126610LN',
                'description': 'Unworn 2024 Rolex Submariner Date in Oystersteel. Complete set with original box, papers, and green seal tag.',
                'category': categories['Luxury Watches'],
                'starting_bid': Decimal('850000.00'),
                'reserve_price': Decimal('950000.00'),
                'buy_now_price': Decimal('1100000.00'),
                'min_bid_increment': Decimal('10000.00'),
                'end_time': now + datetime.timedelta(days=2),
                'bids': [
                    (buyer1, Decimal('860000.00')),
                    (buyer2, Decimal('880000.00')),
                    (buyer1, Decimal('900000.00')),
                ]
            },
            {
                'title': '1968 Shelby GT500 Fastback (Exclusive VIP)',
                'description': 'Restored Mustang Shelby GT500 featuring 428 Cobra Jet V8, 4-speed manual transmission, Wimbledon White with Guardsman Blue stripes.',
                'category': categories['Supercars & Bikes'],
                'starting_bid': Decimal('4500000.00'),
                'reserve_price': Decimal('5000000.00'),
                'buy_now_price': Decimal('6500000.00'),
                'min_bid_increment': Decimal('50000.00'),
                'is_private': True,  # Private auction for Gold/Platinum
                'end_time': now + datetime.timedelta(days=6),
                'bids': [
                    (buyer1, Decimal('4550000.00')),
                ]
            },
            {
                'title': 'Original Oil Painting - Sunset Horizons (1994)',
                'description': 'Authentic hand-painted canvas artwork signed by renowned contemporary artist. Canvas size 36x48 inches.',
                'category': categories['Fine Art'],
                'starting_bid': Decimal('25000.00'),
                'reserve_price': Decimal('35000.00'),
                'buy_now_price': Decimal('50000.00'),
                'min_bid_increment': Decimal('1000.00'),
                'end_time': now + datetime.timedelta(days=3),
                'bids': [
                    (buyer2, Decimal('26000.00')),
                ]
            },
            {
                'title': 'Rare 1999 Charizard 1st Edition Holographic (PSA 9)',
                'description': 'Base set 1st Edition Shadowless Charizard card graded PSA 9 Mint. A true Grail for serious collectors.',
                'category': categories['Collectibles'],
                'starting_bid': Decimal('75000.00'),
                'reserve_price': Decimal('90000.00'),
                'buy_now_price': Decimal('125000.00'),
                'min_bid_increment': Decimal('2500.00'),
                'end_time': now + datetime.timedelta(days=5),
                'bids': [
                    (buyer1, Decimal('77500.00')),
                    (buyer2, Decimal('80000.00')),
                ]
            },
        ]

        for adata in auctions_data:
            auction, created = Auction.objects.get_or_create(
                title=adata['title'],
                defaults={
                    'seller': seller,
                    'description': adata['description'],
                    'category': adata['category'],
                    'starting_bid': adata['starting_bid'],
                    'current_highest_bid': adata['starting_bid'],
                    'reserve_price': adata['reserve_price'],
                    'buy_now_price': adata['buy_now_price'],
                    'min_bid_increment': adata['min_bid_increment'],
                    'is_private': adata.get('is_private', False),
                    'end_time': adata['end_time'],
                    'is_active': True,
                    'is_draft': False,
                }
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f"  Created Auction: {auction.title}"))
                # Place sample bids
                for bidder, amount in adata.get('bids', []):
                    Bid.objects.create(
                        auction=auction,
                        bidder=bidder,
                        amount=amount,
                    )
                    auction.current_highest_bid = amount
                    auction.save()

                # Add sample Watchlist
                Watchlist.objects.get_or_create(user=buyer1, auction=auction)

        # 4. Auto-Bid Setup
        macbook_auction = Auction.objects.filter(title__icontains='MacBook').first()
        if macbook_auction:
            AutoBid.objects.get_or_create(
                auction=macbook_auction,
                bidder=buyer1,
                defaults={'max_amount': Decimal('200000.00'), 'is_active': True}
            )

        # 5. Sample Notifications
        Notification.objects.get_or_create(
            user=buyer1,
            message="Welcome to Elite Auctions! You are currently a Gold VIP member.",
        )
        Notification.objects.get_or_create(
            user=seller,
            message="Your auction 'MacBook Pro M3 Max' has received 4 new bids!",
        )

        self.stdout.write(self.style.SUCCESS("\n[SUCCESS] Successfully seeded database with sample categories, users, auctions & bid logs!"))
        self.stdout.write(self.style.SUCCESS("Demo Accounts Created:"))
        self.stdout.write("   * Admin: admin@example.com (Password: Password123!)")
        self.stdout.write("   * Seller: seller@example.com (Password: Password123!)")
        self.stdout.write("   * Buyer 1: buyer1@example.com (Password: Password123!)")
        self.stdout.write("   * Buyer 2: buyer2@example.com (Password: Password123!)\n")
