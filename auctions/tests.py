from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
import datetime

from auctions.models import User, Category, Auction, Bid, AutoBid, Watchlist, Notification, Order, Payment

class UserModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="Password123!",
            is_buyer=True,
            is_seller=False,
            xp=100
        )

    def test_user_creation(self):
        self.assertEqual(self.user.username, "testuser")
        self.assertEqual(self.user.email, "test@example.com")
        self.assertTrue(self.user.is_buyer)
        self.assertFalse(self.user.is_seller)

    def test_vip_tier(self):
        self.assertEqual(self.user.vip_tier, "Bronze")
        self.user.xp = 600
        self.assertEqual(self.user.vip_tier, "Silver")
        self.user.xp = 2500
        self.assertEqual(self.user.vip_tier, "Gold")
        self.user.xp = 5500
        self.assertEqual(self.user.vip_tier, "Platinum")


class AuctionModelTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user(
            username="seller", email="seller@example.com", password="Password123!", is_seller=True
        )
        self.category = Category.objects.create(name="Electronics", icon="bi-laptop")
        self.auction = Auction.objects.create(
            seller=self.seller,
            title="Gaming Laptop",
            description="High performance laptop",
            category=self.category,
            starting_bid=Decimal("1000.00"),
            reserve_price=Decimal("1500.00"),
            min_bid_increment=Decimal("50.00"),
            end_time=timezone.now() + datetime.timedelta(days=3),
            is_active=True
        )

    def test_auction_initialization(self):
        self.assertEqual(self.auction.current_highest_bid, Decimal("1000.00"))
        self.assertFalse(self.auction.reserve_met)

    def test_reserve_met(self):
        self.auction.current_highest_bid = Decimal("1600.00")
        self.assertTrue(self.auction.reserve_met)

    def test_views_increment(self):
        initial_views = self.auction.views_count
        self.auction.increment_views()
        self.auction.refresh_from_db()
        self.assertEqual(self.auction.views_count, initial_views + 1)


class BiddingLogicTests(TestCase):
    def setUp(self):
        
        self.seller = User.objects.create_user(
            username="seller", email="seller@example.com", password="Password123!", is_seller=True
        )
        self.bidder1 = User.objects.create_user(
            username="bidder1", email="bidder1@example.com", password="Password123!", is_buyer=True
        )
        self.bidder2 = User.objects.create_user(
            username="bidder2", email="bidder2@example.com", password="Password123!", is_buyer=True
        )
        self.category = Category.objects.create(name="Art", icon="bi-palette")
        self.auction = Auction.objects.create(
            seller=self.seller,
            title="Vintage Painting",
            description="Rare oil painting",
            category=self.category,
            starting_bid=Decimal("500.00"),
            min_bid_increment=Decimal("50.00"),
            end_time=timezone.now() + datetime.timedelta(days=1),
            is_active=True
        )
        self.client = Client()

    def test_place_bid_valid(self):
        self.client.login(email="bidder1@example.com", password="Password123!")
        response = self.client.post(
            reverse('place_bid', args=[self.auction.id]),
            {'bid_amount': '550.00'}
        )
        self.assertEqual(response.status_code, 302)
        self.auction.refresh_from_db()
        self.assertEqual(self.auction.current_highest_bid, Decimal("550.00"))
        self.assertEqual(Bid.objects.filter(auction=self.auction).count(), 1)

    def test_place_bid_too_low(self):
        self.client.login(email="bidder1@example.com", password="Password123!")
        response = self.client.post(
            reverse('place_bid', args=[self.auction.id]),
            {'bid_amount': '520.00'} # less than 500 + 50
        )
        self.assertEqual(response.status_code, 302)
        self.auction.refresh_from_db()
        self.assertEqual(self.auction.current_highest_bid, Decimal("500.00"))

    def test_seller_cannot_bid_on_own_auction(self):
        self.client.login(email="seller@example.com", password="Password123!")
        response = self.client.post(
            reverse('place_bid', args=[self.auction.id]),
            {'bid_amount': '600.00'}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Bid.objects.filter(auction=self.auction).count(), 0)


class ViewsIntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.seller = User.objects.create_user(
            username="seller", email="seller@example.com", password="Password123!", is_seller=True
        )
        self.category = Category.objects.create(name="Books")
        self.auction = Auction.objects.create(
            seller=self.seller,
            title="First Edition Book",
            description="Collectible book",
            category=self.category,
            starting_bid=Decimal("100.00"),
            end_time=timezone.now() + datetime.timedelta(days=2),
            is_active=True
        )

    def test_auction_list_view(self):
        response = self.client.get(reverse('auction_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "First Edition Book")

    def test_auction_detail_view(self):
        self.client.login(email="seller@example.com", password="Password123!")
        response = self.client.get(reverse('auction_detail', args=[self.auction.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "First Edition Book")
