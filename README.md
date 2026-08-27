# Elite Auctions — Advanced Online Luxury Auction & Bidding Platform 🎓

> **College Project Submission**  
> **Course / Degree**: B.Tech / B.E. / M.C.A. Computer Science & Software Engineering  
> **Technology Stack**: Python 3.10+, Django 4.x, WebSockets (Django Channels), Razorpay Payments, PostgreSQL / SQLite, HTML5, Vanilla CSS3 (Obsidian Dark Glassmorphism), Chart.js  

---

## 📌 Project Abstract & Overview

**Elite Auctions** is a full-stack, real-time web application engineered for high-value asset auctions, rare collectibles, fine art, luxury automobiles, and premium electronics. The platform replaces traditional, manual auction mechanisms with a secure, automated, transparent bidding ecosystem.

Key capabilities include **real-time WebSocket bidding synchronization**, **automated proxy auto-bidding algorithms**, **hidden reserve price verification**, **Razorpay Escrow payment integration with cryptographic signature verification**, **3D asset viewing (`.glb`/`.gltf`)**, **automated winner notifications via email**, and a real-time **Admin Analytics Command Center**.

---

## 🚀 Key Features & Architectural Modules

### 1. 🔐 Authentication & Security Module
- **Dual Authentication**: Standard Username/Password + Social OAuth (Google & GitHub) via `django-allauth`.
- **Environment Isolation**: Production secrets managed via `python-decouple` (`.env`).
- **Security Audit Logs**: Automated tracking of login attempts, payment verifications, and suspicious action flagging (`SecurityLog`).

### 2. ⚡ Real-Time Bidding Engine
- **Live WebSocket Feeds**: Real-time bid price updates and live bid history synchronization across all connected buyers without page refreshes.
- **Proxy Auto-Bids (`AutoBid`)**: Algorithmic proxy bidding up to a user-defined max cap. Automatically places minimal incremental bids when outbid.
- **Reserve Price & Buy Now**: Hidden reserve price logic (only sells if met) + instant Buy Now payment trigger.
- **Minimum Bid Increments**: Enforced step-bidding rules (e.g. +₹50, +₹100, +₹500).

### 3. 🎨 Obsidian Dark Glassmorphism UI/UX
- **Unified Design System**: Glass panels (`backdrop-filter: blur`), dark obsidian palette (`#090d16`), vibrant neon accents (`#6366f1` / `#22d3ee`).
- **Modern Typography**: Google Fonts (`Plus Jakarta Sans` & `Space Grotesk`).
- **Interactive Visuals**: Hero carousel, glass search bar, category shortcuts, live countdown timers, 3D model viewer, and Chart.js line charts.

### 4. 💳 Payments, Escrow & Order Tracking
- **Razorpay Integration**: Cryptographic signature verification (`HMAC-SHA256`) preventing URL forgery.
- **Escrow Workflow**: Funds held securely until item delivery confirmation.
- **Order Tracking Timeline**: Workflow stages (`PROCESSING` ➔ `SHIPPED` ➔ `OUT_FOR_DELIVERY` ➔ `DELIVERED`).
- **Ratings & Reviews**: Buyer seller rating system (1 to 5 stars).

### 5. 📊 Admin Command Center & Reporting
- Real-time KPI counters: total revenue, active disputes, bid velocity, category distributions.
- Automated PDF Sales Report generation.
- Automated background tasks via `APScheduler` for expiring auction finalization.

---

## 🛠 Tech Stack Details

| Layer | Technology |
| :--- | :--- |
| **Backend Framework** | Django 4.x (Python 3.10+) |
| **Real-Time WebSockets**| Django Channels + WebSockets |
| **Database** | PostgreSQL / SQLite |
| **Background Scheduler** | APScheduler |
| **Payment Gateway** | Razorpay SDK (Signature Verified) |
| **OAuth Providers** | Google & GitHub OAuth 2.0 (`django-allauth`) |
| **Frontend Technologies**| HTML5, Vanilla CSS3 (Custom Glassmorphic Design System) |
| **Data Visualization** | Chart.js |
| **3D Rendering** | `<model-viewer>` Web Component (.glb / .gltf) |

---

## ⚙️ Installation & Local Setup Guide

Follow these steps to run the project on your local machine for evaluation:

### 1. Clone & Navigate to Repository
```bash
git clone <repository_url>
cd E_auction
```

### 2. Create and Activate Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
*(Ensure `SECRET_KEY`, `DEBUG`, and Razorpay keys are configured in `.env`)*

### 5. Apply Database Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Create Superuser (Admin Account)
```bash
python manage.py createsuperuser
```

### 7. Run Development Server
```bash
python manage.py runserver
```

Open your browser and navigate to:
- **Marketplace Web App**: `http://127.0.0.1:8000/`
- **Admin Command Center**: `http://127.0.0.1:8000/admin-dashboard/`
- **Django Admin Portal**: `http://127.0.0.1:8000/admin/`

---

## 🧪 Running Automated Tests

To execute the test suite:
```bash
python manage.py test
```
*Expected Output: `Ran 10 tests... OK`*

---

## 📁 Repository Structure Overview

```
d:\E_auction/
├── auctions/              # Core Django Application (Models, Views, Signals, Consumers)
├── core/                  # Project Configuration (Settings, ASGI, WSGI, URLs)
├── static/                # Static Assets (CSS Design System, JS, Images)
│   ├── css/style.css      # Obsidian Glass Design System
│   └── js/                # Password toggles & WebSocket helpers
├── templates/             # HTML Templates (Base, Marketplace, Auction Detail, Admin)
│   ├── auctions/          # Marketplace, Detail, Dashboard, Orders, Receipts
│   └── registration/      # Login, Register, Profiles, Auth forms
├── .env.example           # Environment template
├── IMPLEMENTATION_SUMMARY.md # Detailed technical feature summary
├── manage.py              # Django CLI entrypoint
└── requirements.txt       # Python dependencies manifest
```

---

## 📜 Academic Declaration

This project has been developed independently as part of the academic coursework requirement. All security standards, data models, WebSocket protocols, and custom design systems have been implemented adhering to software engineering best practices.
