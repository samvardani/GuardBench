<!-- f035aae5-7ca0-418e-ab33-003d15a93899 d41985f0-008b-4259-b658-c6fabf4d2559 -->
# Vxirtual Staging & Listing Prep Platform

Build a complete platform for a virtual staging and listing prep service targeting Seattle/Eastside real estate market, with Vancouver BC waitlist support.

## Project Structure

Create new directory: `virtual-staging/` with the following structure:

```
virtual-staging/
├── backend/              # FastAPI backend
│   ├── src/
│   │   ├── api/         # API routes
│   │   ├── models/      # Pydantic models
│   │   ├── db/          # Database layer
│   │   ├── services/    # Business logic
│   │   └── config.py    # Configuration
│   ├── requirements.txt
│   └── main.py          # FastAPI app entry
├── frontend/            # Marketing website & dashboard
│   ├── public/          # Static assets
│   ├── pages/           # HTML pages
│   │   ├── index.html   # Homepage
│   │   ├── services.html
│   │   ├── packages.html
│   │   ├── portfolio.html
│   │   ├── about.html
│   │   ├── contact.html
│   │   └── vancouver-waitlist.html
│   └── dashboard/       # Business management dashboard
│       ├── index.html   # Dashboard home
│       ├── jobs.html    # Job management
│       ├── clients.html # Client CRM
│       ├── analytics.html # KPIs
│       └── settings.html
├── docs/                # Documentation
│   ├── README.md
│   ├── API.md
│   ├── SOPs.md
│   └── business-plan.md
└── data/                # Data storage
    ├── db/              # SQLite database
    └── uploads/         # Client uploads
```

## Implementation Tasks

### 1. Backend API (FastAPI)

**Database Schema** (`backend/src/db/schema.py`):

- `clients` table (name, email, phone, segment, created_at)
- `jobs` table (client_id, tier, status, photos_link, style, sla_deadline, created_at)
- `packages` table (tier, name, price_band, inclusions JSON)
- `revisions` table (job_id, round_number, feedback, status)
- `kpis` table (metric_name, value, timestamp, job_id)

**API Routes** (`backend/src/api/`):

- `/api/v1/clients` - CRUD for clients
- `/api/v1/jobs` - Job management (create, list, update status)
- `/api/v1/packages` - Package definitions
- `/api/v1/revisions` - Revision tracking
- `/api/v1/kpis` - KPI metrics
- `/api/v1/intake` - Client intake form submission
- `/api/v1/batch` - Batch job processing (CSV upload)
- `/api/v1/analytics` - Dashboard analytics

**Services** (`backend/src/services/`):

- `job_service.py` - Job lifecycle management
- `sla_service.py` - SLA calculation and tracking
- `batch_service.py` - Batch processing logic
- `analytics_service.py` - KPI calculations

**Models** (`backend/src/models/`):

- Pydantic models matching the JSON spec (Client, Job, Package, Revision, KPI)

### 2. Marketing Website

**Homepage** (`frontend/pages/index.html`):

- Hero section with positioning statement
- Three pillars (Speed & Reliability, Batch & Scale, Ethical MLS-Safe Staging)
- Package overview cards (T1, T2, T3)
- Micro-offers section
- CTA buttons (Get Quote, Contact)

**Services Page** (`frontend/pages/services.html`):

- Detailed package descriptions
- Pricing bands
- SLA information
- Add-ons and revisions policy

**Portfolio Page** (`frontend/pages/portfolio.html`):

- Before/after image gallery
- Case studies
- Market focus (Seattle/Eastside)

**About/Ethics Page** (`frontend/pages/about.html`):

- Ethics policy (vacancy-only, MLS disclosure)
- Scope boundaries
- Watermark policy

**Contact/Waitlist** (`frontend/pages/vancouver-waitlist.html`):

- Vancouver waitlist form
- Contact form for Seattle inquiries

**Design System**:

- Tailwind CSS (CDN) matching existing dark mode aesthetic
- Responsive design (mobile-first)
- Professional, clean styling
- Seattle/Eastside branding

### 3. Business Management Dashboard

**Dashboard Home** (`frontend/dashboard/index.html`):

- KPI cards (Revenue, Quote-to-Close %, Avg Revisions, etc.)
- Recent jobs table
- Upcoming SLA deadlines
- Quick actions

**Jobs Management** (`frontend/dashboard/jobs.html`):

- Job list with filters (status, tier, client)
- Job detail view (photos, timeline, revisions)
- Status workflow (Intake → In Progress → QA → Delivered)
- SLA countdown timers

**Clients CRM** (`frontend/dashboard/clients.html`):

- Client list with segment tags
- Client detail (jobs history, preferences)
- Quick quote generation

**Analytics** (`frontend/dashboard/analytics.html`):

- KPI charts (revenue trends, conversion rates)
- Service mix breakdown (T1/T2/T3)
- Channel attribution
- Time-per-job metrics

**Settings** (`frontend/dashboard/settings.html`):

- Package configuration
- SLA rules
- Revision policies
- Batch rules

**Tech Stack**:

- React (CDN) for interactivity
- Tailwind CSS for styling
- Fetch API for backend calls
- LocalStorage for auth state

### 4. Documentation

**README.md**:

- Project overview
- Setup instructions
- Architecture overview

**API.md**:

- API endpoint documentation
- Request/response examples
- Authentication

**SOPs.md**:

- SOP-01: Virtual Client Intake
- SOP-02: Virtual Staging Batch Run
- SOP-03: Hybrid Prep Day-of-Execution

**business-plan.md**:

- Personas summary
- Pricing strategy
- Market positioning
- Risk mitigation

## Key Features

1. **Multi-tier Packages**: T1 (Virtual-only), T2 (Hybrid), T3 (Signature Estate)
2. **SLA Tracking**: Automatic deadline calculation based on cutoffs
3. **Batch Processing**: CSV intake for 10+ unit batches
4. **Revision Management**: Consolidated round tracking per tier
5. **KPI Dashboard**: Real-time metrics from spec
6. **Ethics Compliance**: Vacancy-only policy enforcement
7. **Regional Support**: Seattle primary, Vancouver waitlist

## Technical Decisions

- **Database**: SQLite (simple, file-based, matches existing pattern)
- **Backend**: FastAPI (matches existing codebase)
- **Frontend**: Vanilla HTML + React CDN (matches dashboard pattern)
- **Styling**: Tailwind CSS CDN (matches existing dashboards)
- **File Upload**: FastAPI multipart (for photos/CSV)

## Integration Points

- Use existing FastAPI patterns from `src/service/api.py`
- Follow Pydantic model patterns from existing codebase
- Match dashboard styling from `dashboard/index.html`
- Use similar auth patterns if needed (can start simple)

### To-dos

- [ ] Create virtual-staging/ directory structure with backend/, frontend/, docs/, and data/ subdirectories
- [ ] Implement database schema (clients, jobs, packages, revisions, kpis tables) in backend/src/db/schema.py
- [ ] Create Pydantic models for Client, Job, Package, Revision, KPI matching the JSON spec
- [ ] Implement FastAPI routes for clients, jobs, packages, revisions, KPIs, intake, batch, and analytics
- [ ] Implement business logic services (job_service, sla_service, batch_service, analytics_service)
- [ ] Build marketing homepage (index.html) with hero, pillars, packages, micro-offers, and CTAs
- [ ] Create services, portfolio, about, contact, and Vancouver waitlist pages
- [ ] Build dashboard home page with KPI cards, recent jobs, SLA deadlines, and quick actions
- [ ] Create jobs management page with list, filters, detail view, status workflow, and SLA timers
- [ ] Build clients CRM page with list, detail view, segment tags, and quote generation
- [ ] Create analytics page with KPI charts, service mix, channel attribution, and time metrics
- [ ] Build settings page for package config, SLA rules, revision policies, and batch rules
- [ ] Create README.md, API.md, SOPs.md, and business-plan.md documentation files