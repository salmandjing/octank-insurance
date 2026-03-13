# Nebraska Insurance FNOL Automation — Claude Code Build Spec

## Project Overview

Convert an existing agentic virtual agent prototype (Octank Insurance, built for a Genesys Cloud CX presales demo) into a standalone FNOL (First Notice of Loss) automation product targeting independent insurance agencies in Nebraska. The existing prototype uses AWS Bedrock (Claude 3.5 Haiku + Sonnet), FastAPI, vanilla JS frontend, multi-agent orchestration, RAG, guardrails, and a human agent desktop. This spec defines how to repurpose and extend that codebase into a demo-ready product for selling to Nebraska insurance agencies.

**Goal**: A working demo that can be screen-recorded or shown live to an insurance agency owner. The demo should show: an email or form claim coming in → AI extracting structured FNOL data → policy verification → carrier submission draft → client confirmation draft → human review dashboard. The agency owner should immediately understand "this replaces 30-60 minutes of manual work per claim."

**Target user**: Independent insurance agency in Nebraska (5-30 employees), using an agency management system (Applied Epic, Hawksoft, AMS360, or QQ Catalyst). Writes auto, homeowners, commercial property, farm/ranch, and workers comp. Works with 10-20 carriers.

**Tech constraints**: Keep the existing stack (Python 3.11+, FastAPI, vanilla JS frontend). Switch from AWS Bedrock to Anthropic API directly (Claude Sonnet 4 via `anthropic` Python SDK). No cloud infrastructure — everything runs locally for demos. Mock all external integrations (agency management system, carrier portals) with realistic fake data.

---

## Phase 1: Rebrand and Restructure

### 1.1 Rename the project
- Remove all Octank Insurance branding, Genesys references, and presales-specific features
- New project name: **ClaimFlow AI** (or similar — pick something clean)
- Update all UI text, page titles, favicon, etc.
- Remove: Discovery Mode (D key), Architecture Modal (G key), Genesys mapping overlays, multi-region toggle, latency simulation toggle
- Keep: Under the Hood / observability panel (rename to "AI Transparency" — agencies will love seeing how the AI thinks)

### 1.2 Restructure the codebase

**Current structure to preserve and extend:**
```
prototype/
├── backend/
│   ├── main.py                    → Keep, heavily modify routes
│   ├── config.py                  → Update for Anthropic API
│   ├── models.py                  → Extend with new Pydantic models
│   ├── agents/
│   │   ├── base.py                → Update LLM calls to Anthropic SDK
│   │   ├── supervisor.py          → Modify classification categories
│   │   ├── fnol.py                → Major rewrite — core of the product
│   │   ├── eligibility.py         → Repurpose as policy_lookup.py
│   │   └── claims.py              → Keep for claim status queries
│   ├── tools/                     → Replace mock tools with realistic mocks
│   ├── rag/                       → Keep architecture, replace docs
│   ├── guardrails/                → Extend for insurance compliance
│   └── state/                     → Extend session model
├── frontend/
│   ├── index.html                 → Redesign screens
│   ├── app.js                     → Major UI rewrite
│   └── styles.css                 → New design system
```

**New files/directories to add:**
```
├── backend/
│   ├── agents/
│   │   ├── email_parser.py        → NEW: Email intake parsing agent
│   │   ├── coi_generator.py       → NEW: Certificate of Insurance agent
│   │   └── renewal_checker.py     → NEW: Policy renewal monitoring agent
│   ├── tools/
│   │   ├── ams_api.py             → NEW: Mock Agency Management System API
│   │   ├── carrier_api.py         → NEW: Mock carrier submission API
│   │   ├── email_intake.py        → NEW: Email parsing and attachment handling
│   │   └── document_generator.py  → NEW: Generate carrier forms and client letters
│   ├── carriers/
│   │   ├── templates/             → NEW: Carrier-specific FNOL form templates
│   │   │   ├── erie.json
│   │   │   ├── auto_owners.json
│   │   │   ├── westfield.json
│   │   │   ├── emcasco.json
│   │   │   └── grinnell_mutual.json
│   │   └── router.py              → NEW: Routes claims to correct carrier format
│   └── data/
│       ├── members.json           → Replace with realistic Nebraska agency clients
│       ├── policies.json          → NEW: Detailed policy records
│       ├── claims.json            → Replace with realistic claims
│       ├── carriers.json          → NEW: Carrier directory with submission requirements
│       └── docs/                  → Replace with real insurance procedure docs
```

### 1.3 Switch from AWS Bedrock to Anthropic API

Replace all Bedrock `invoke_model` calls with the `anthropic` Python SDK.

```python
# Old (Bedrock)
import boto3
client = boto3.client('bedrock-runtime')
response = client.invoke_model(modelId="us.anthropic.claude-3-5-sonnet-...", body=...)

# New (Anthropic direct)
import anthropic
client = anthropic.Anthropic()  # Uses ANTHROPIC_API_KEY env var
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4096,
    messages=[...],
    tools=[...]  # Native tool use
)
```

Update `config.py`:
```python
SUPERVISOR_MODEL = "claude-sonnet-4-20250514"  # Use Sonnet for everything now
SPECIALIST_MODEL = "claude-sonnet-4-20250514"
# Haiku was used for cost optimization in the Genesys demo.
# For this product demo, Sonnet everywhere is fine — quality matters more than cost.
```

Update `.env.example`:
```
ANTHROPIC_API_KEY=sk-ant-...
```

Update `requirements.txt` — remove `boto3`, add `anthropic`.

---

## Phase 2: Mock Data — Make It Feel Like Nebraska

This is critical. The demo must feel real to a Nebraska agency owner. Generic "John Smith" data won't cut it. Everything should feel like a real agency's book of business.

### 2.1 Agency Profile

Create a fictional agency: **Prairie Shield Insurance Group** based in Omaha, NE. Independent agency, 12 employees, writes personal and commercial lines. Licensed with the Nebraska Department of Insurance. Works with 8 carriers.

### 2.2 Mock Clients (members.json → clients.json)

Create 10 realistic clients. Mix of personal and commercial. Nebraska-appropriate names, addresses, and scenarios.

```json
[
  {
    "id": "CLI-1001",
    "name": "Tom Rezac",
    "type": "personal",
    "address": "4821 Dodge St, Omaha, NE 68132",
    "phone": "(402) 555-0147",
    "email": "tom.rezac@email.com",
    "policies": ["POL-PA-2024-001", "POL-HO-2024-001"],
    "preferred_contact": "email",
    "agent": "Lisa Novak",
    "since": "2018-03-15",
    "notes": "Referred by his brother Mike. Owns a landscaping business — ask about commercial GL renewal in Q3."
  },
  {
    "id": "CLI-1002",
    "name": "Karen Pflug",
    "type": "personal",
    "address": "1205 S 90th St, Lincoln, NE 68520",
    "phone": "(402) 555-0283",
    "email": "kpflug@gmail.com",
    "policies": ["POL-PA-2024-002", "POL-HO-2024-002", "POL-UMB-2024-001"],
    "preferred_contact": "phone",
    "agent": "Lisa Novak",
    "since": "2015-07-22"
  },
  {
    "id": "CLI-1003",
    "name": "Heartland Ag Supply LLC",
    "type": "commercial",
    "address": "8901 Cornhusker Hwy, Lincoln, NE 68507",
    "phone": "(402) 555-0391",
    "email": "accounting@heartlandag.com",
    "contact_person": "Dave Kowalski",
    "policies": ["POL-BOP-2024-001", "POL-CA-2024-001", "POL-WC-2024-001", "POL-GL-2024-001"],
    "preferred_contact": "email",
    "agent": "Mark Jansen",
    "since": "2012-01-10",
    "notes": "Largest commercial account. 22 vehicles on commercial auto. Annual review every November."
  },
  {
    "id": "CLI-1004",
    "name": "Jim and Nancy Schroeder",
    "type": "personal",
    "address": "Rural Route 2, Box 44, York, NE 68467",
    "phone": "(402) 555-0512",
    "email": "schroeder.farm@yahoo.com",
    "policies": ["POL-FR-2024-001", "POL-PA-2024-003"],
    "preferred_contact": "phone",
    "agent": "Mark Jansen",
    "since": "2009-11-03",
    "notes": "Farm/ranch policy. 640 acres, cattle operation. Grain bins added in 2023."
  },
  {
    "id": "CLI-1005",
    "name": "Elkhorn Creek Dental",
    "type": "commercial",
    "address": "2340 N 120th St, Omaha, NE 68164",
    "phone": "(402) 555-0678",
    "email": "office@elkhorndentalomaha.com",
    "contact_person": "Dr. Sarah Pham",
    "policies": ["POL-BOP-2024-002", "POL-PL-2024-001", "POL-WC-2024-002"],
    "preferred_contact": "email",
    "agent": "Lisa Novak",
    "since": "2020-06-15",
    "notes": "Professional liability is critical — malpractice coverage. 3 dentists, 8 staff."
  },
  {
    "id": "CLI-1006",
    "name": "Miguel Torres",
    "type": "personal",
    "address": "3567 Vinton St, Omaha, NE 68105",
    "phone": "(402) 555-0834",
    "email": "mtorres84@gmail.com",
    "policies": ["POL-PA-2024-004", "POL-REN-2024-001"],
    "preferred_contact": "email",
    "agent": "Lisa Novak",
    "since": "2022-09-01",
    "notes": "Renter's policy. Recently bought a new car — updated from liability-only to full coverage."
  },
  {
    "id": "CLI-1007",
    "name": "Great Plains Trucking Inc",
    "type": "commercial",
    "address": "5600 F St, Omaha, NE 68117",
    "phone": "(402) 555-0945",
    "email": "dispatch@gptrucking.com",
    "contact_person": "Randy Becker",
    "policies": ["POL-CA-2024-002", "POL-GL-2024-002", "POL-WC-2024-003", "POL-MTC-2024-001"],
    "preferred_contact": "phone",
    "agent": "Mark Jansen",
    "since": "2016-04-20",
    "notes": "Motor truck cargo. 14 rigs. High claim frequency — 3 claims in last 12 months. Watch loss ratio."
  },
  {
    "id": "CLI-1008",
    "name": "Linda Sorensen",
    "type": "personal",
    "address": "912 W 4th St, Grand Island, NE 68801",
    "phone": "(308) 555-0123",
    "email": "linda.sorensen@outlook.com",
    "policies": ["POL-PA-2024-005", "POL-HO-2024-003"],
    "preferred_contact": "phone",
    "agent": "Mark Jansen",
    "since": "2017-02-28",
    "notes": "Hail damage claim last year. Lives in high-hail zone — discussed impact-resistant roof discount."
  },
  {
    "id": "CLI-1009",
    "name": "Aksarben Property Management",
    "type": "commercial",
    "address": "6700 Mercy Rd, Suite 400, Omaha, NE 68106",
    "phone": "(402) 555-0267",
    "email": "claims@aksarbenprop.com",
    "contact_person": "Angela Wu",
    "policies": ["POL-CP-2024-001", "POL-GL-2024-003", "POL-UMB-2024-002"],
    "preferred_contact": "email",
    "agent": "Lisa Novak",
    "since": "2014-08-12",
    "notes": "Manages 12 apartment complexes in Omaha metro. High COI request volume — 20+ per month."
  },
  {
    "id": "CLI-1010",
    "name": "Brett and Amy Christensen",
    "type": "personal",
    "address": "2100 Pioneers Blvd, Lincoln, NE 68502",
    "phone": "(402) 555-0389",
    "email": "bchristensen@unl.edu",
    "policies": ["POL-PA-2024-006", "POL-PA-2024-007", "POL-HO-2024-004"],
    "preferred_contact": "email",
    "agent": "Lisa Novak",
    "since": "2019-05-20",
    "notes": "Two autos on policy. UNL professor. Daughter turning 16 next month — will need to add driver."
  }
]
```

### 2.3 Mock Policies (policies.json — NEW)

Create detailed policy records that link to clients. Include coverage types, limits, deductibles, effective dates, and carrier assignments. Use real Nebraska carriers that independent agencies actually work with.

```json
[
  {
    "id": "POL-PA-2024-001",
    "client_id": "CLI-1001",
    "type": "personal_auto",
    "carrier": "Auto-Owners Insurance",
    "carrier_id": "CARRIER-AO",
    "policy_number": "AO-PA-8847321",
    "effective_date": "2024-06-15",
    "expiration_date": "2025-06-15",
    "status": "active",
    "vehicles": [
      {
        "year": 2022,
        "make": "Ford",
        "model": "F-150 XLT",
        "vin": "1FTFW1E85NFA12345",
        "coverage": {
          "liability": {"bi_per_person": 100000, "bi_per_accident": 300000, "pd": 100000},
          "collision": {"deductible": 500},
          "comprehensive": {"deductible": 250},
          "uninsured_motorist": {"bi_per_person": 100000, "bi_per_accident": 300000},
          "medical_payments": 5000
        }
      }
    ],
    "premium_annual": 1847.00,
    "payment_plan": "monthly",
    "drivers": [
      {"name": "Tom Rezac", "license": "NE-A12345678", "dob": "1985-03-22", "relation": "insured"}
    ]
  },
  {
    "id": "POL-HO-2024-001",
    "client_id": "CLI-1001",
    "type": "homeowners",
    "carrier": "Erie Insurance",
    "carrier_id": "CARRIER-ERIE",
    "policy_number": "ERIE-HO-Q442891",
    "effective_date": "2024-04-01",
    "expiration_date": "2025-04-01",
    "status": "active",
    "property": {
      "address": "4821 Dodge St, Omaha, NE 68132",
      "year_built": 1978,
      "sqft": 2400,
      "construction": "frame",
      "roof_type": "architectural_shingle",
      "roof_year": 2019
    },
    "coverage": {
      "dwelling": 340000,
      "other_structures": 34000,
      "personal_property": 170000,
      "loss_of_use": 68000,
      "personal_liability": 300000,
      "medical_payments": 5000,
      "deductible": 1000,
      "wind_hail_deductible": "2_percent"
    },
    "premium_annual": 2156.00,
    "endorsements": ["water_backup", "identity_theft", "scheduled_jewelry_3500"]
  },
  {
    "id": "POL-CA-2024-001",
    "client_id": "CLI-1003",
    "type": "commercial_auto",
    "carrier": "EMC Insurance (EMCASCO)",
    "carrier_id": "CARRIER-EMC",
    "policy_number": "EMC-CA-BZ-224891",
    "effective_date": "2024-01-01",
    "expiration_date": "2025-01-01",
    "status": "active",
    "vehicles_count": 22,
    "coverage": {
      "liability": {"csl": 1000000},
      "collision": {"deductible": 1000},
      "comprehensive": {"deductible": 1000},
      "uninsured_motorist": {"csl": 1000000},
      "hired_auto": true,
      "non_owned_auto": true
    },
    "premium_annual": 38450.00
  },
  {
    "id": "POL-FR-2024-001",
    "client_id": "CLI-1004",
    "type": "farm_ranch",
    "carrier": "Grinnell Mutual",
    "carrier_id": "CARRIER-GRIN",
    "policy_number": "GM-FR-NE-445672",
    "effective_date": "2024-03-01",
    "expiration_date": "2025-03-01",
    "status": "active",
    "property": {
      "address": "Rural Route 2, Box 44, York, NE 68467",
      "acreage": 640,
      "dwelling_value": 280000,
      "barn_value": 120000,
      "grain_bins": [
        {"capacity_bushels": 30000, "value": 45000, "year": 2015},
        {"capacity_bushels": 30000, "value": 45000, "year": 2015},
        {"capacity_bushels": 20000, "value": 52000, "year": 2023}
      ],
      "machinery_scheduled": 385000,
      "livestock": {"type": "beef_cattle", "head_count": 180, "value": 324000}
    },
    "coverage": {
      "dwelling": 280000,
      "farm_structures": 262000,
      "farm_personal_property": 385000,
      "livestock": 324000,
      "liability": 500000,
      "deductible": 2500
    },
    "premium_annual": 6840.00
  }
]
```

Create at least 8-10 policies covering: personal auto, homeowners, commercial auto, commercial property/BOP, farm/ranch, workers comp, general liability, professional liability. Each with realistic Nebraska-appropriate data.

### 2.4 Mock Carriers (carriers.json — NEW)

```json
[
  {
    "id": "CARRIER-AO",
    "name": "Auto-Owners Insurance",
    "lines": ["personal_auto", "homeowners", "commercial_auto", "commercial_property", "umbrella"],
    "fnol_method": "portal",
    "fnol_portal_url": "https://claims.auto-owners.com",
    "fnol_phone": "1-888-252-4626",
    "claims_email": "claims@auto-owners.com",
    "required_fnol_fields": ["policy_number", "date_of_loss", "time_of_loss", "location", "description", "claimant_contact", "police_report_number", "injuries", "other_parties"],
    "submission_format": "acord_form",
    "avg_response_time_hours": 24,
    "adjuster_assignment": "auto"
  },
  {
    "id": "CARRIER-ERIE",
    "name": "Erie Insurance",
    "lines": ["personal_auto", "homeowners", "commercial_property"],
    "fnol_method": "portal_and_email",
    "fnol_portal_url": "https://erieinsurance.com/claims",
    "fnol_phone": "1-800-367-3743",
    "claims_email": "newclaims@erieinsurance.com",
    "required_fnol_fields": ["policy_number", "date_of_loss", "location", "description", "claimant_contact", "photos", "injuries", "emergency_services_called"],
    "submission_format": "erie_digital",
    "avg_response_time_hours": 12
  },
  {
    "id": "CARRIER-EMC",
    "name": "EMC Insurance (EMCASCO)",
    "lines": ["commercial_auto", "commercial_property", "general_liability", "workers_comp", "farm_ranch"],
    "fnol_method": "portal",
    "fnol_portal_url": "https://emcins.com/claims",
    "fnol_phone": "1-800-362-2227",
    "required_fnol_fields": ["policy_number", "date_of_loss", "time_of_loss", "location", "description", "claimant_contact", "injuries", "police_report_number", "estimated_damage", "witness_info"],
    "submission_format": "acord_form"
  },
  {
    "id": "CARRIER-GRIN",
    "name": "Grinnell Mutual",
    "lines": ["farm_ranch", "homeowners", "personal_auto", "commercial_property"],
    "fnol_method": "phone_and_email",
    "fnol_phone": "1-800-362-2041",
    "claims_email": "claimsreport@grinnellmutual.com",
    "required_fnol_fields": ["policy_number", "date_of_loss", "location", "description", "claimant_contact", "injuries", "type_of_loss"],
    "submission_format": "custom_form"
  },
  {
    "id": "CARRIER-WF",
    "name": "Westfield Insurance",
    "lines": ["personal_auto", "homeowners", "commercial_property", "general_liability"],
    "fnol_method": "portal",
    "fnol_portal_url": "https://westfieldinsurance.com/claims",
    "fnol_phone": "1-800-243-0210",
    "required_fnol_fields": ["policy_number", "date_of_loss", "time_of_loss", "location", "description", "claimant_contact", "police_report_number"],
    "submission_format": "acord_form"
  }
]
```

### 2.5 Mock Claims (claims.json — replace existing)

Create 5-6 realistic Nebraska claims in various states. Include Nebraska-specific scenarios: hail damage, cattle on the road, farm equipment accident, pipe freeze, fender bender on I-80.

```json
[
  {
    "id": "CLM-2024-0891",
    "client_id": "CLI-1008",
    "policy_id": "POL-HO-2024-003",
    "carrier": "Westfield Insurance",
    "type": "homeowners",
    "peril": "hail",
    "date_of_loss": "2024-06-14",
    "date_reported": "2024-06-15",
    "status": "under_review",
    "description": "Severe hail storm hit Grand Island area. Quarter-sized hail for approximately 20 minutes. Roof damage — missing and cracked shingles visible. Dents on north-facing aluminum siding. Two skylights cracked. Gutter damage on east side. No interior water damage yet but concerned about next rain.",
    "adjuster": {"name": "Pat Greenfield", "phone": "(402) 555-9012", "email": "pgreenfield@westfield.com"},
    "estimated_damage": 18500,
    "police_report": false,
    "photos_submitted": true,
    "timeline": [
      {"date": "2024-06-15", "event": "FNOL submitted by agency"},
      {"date": "2024-06-16", "event": "Adjuster assigned"},
      {"date": "2024-06-18", "event": "Inspection scheduled for 6/20"},
      {"date": "2024-06-20", "event": "Inspection completed. Roof replacement recommended."},
      {"date": "2024-06-22", "event": "Estimate sent to insured. Pending approval."}
    ]
  },
  {
    "id": "CLM-2024-1204",
    "client_id": "CLI-1001",
    "policy_id": "POL-PA-2024-001",
    "carrier": "Auto-Owners Insurance",
    "type": "personal_auto",
    "peril": "collision",
    "date_of_loss": "2024-11-02",
    "date_reported": "2024-11-02",
    "status": "open",
    "description": "Rear-ended at stoplight on 72nd and Dodge. Other driver ran red light. Police report filed. No injuries. Bumper damage and possible frame misalignment. Other driver insured — State Farm policy. Other driver's info: Maria Gonzales, State Farm policy SF-4412876.",
    "adjuster": null,
    "estimated_damage": 4200,
    "police_report": true,
    "police_report_number": "OPD-2024-889431",
    "photos_submitted": false,
    "timeline": [
      {"date": "2024-11-02", "event": "FNOL submitted by agency"}
    ]
  },
  {
    "id": "CLM-2024-0673",
    "client_id": "CLI-1004",
    "policy_id": "POL-FR-2024-001",
    "carrier": "Grinnell Mutual",
    "type": "farm_ranch",
    "peril": "wind",
    "date_of_loss": "2024-08-28",
    "date_reported": "2024-08-29",
    "status": "approved",
    "description": "Straight-line winds from severe thunderstorm. Estimated 70-80 mph. Older barn (north barn) partially collapsed — west wall and portion of roof down. Two grain bins dented, one with roof damage. Fence line down along highway 81 — approximately 400 feet. 12 head of cattle got out, all recovered. No injuries to livestock or people.",
    "adjuster": {"name": "Steve Holman", "phone": "(515) 555-3456", "email": "sholman@grinnellmutual.com"},
    "estimated_damage": 67000,
    "approved_amount": 61500,
    "police_report": false,
    "photos_submitted": true,
    "timeline": [
      {"date": "2024-08-29", "event": "FNOL submitted by agency"},
      {"date": "2024-08-29", "event": "Adjuster assigned — expedited due to livestock safety concern"},
      {"date": "2024-08-30", "event": "Field inspection completed"},
      {"date": "2024-09-05", "event": "Estimate finalized: $67,000"},
      {"date": "2024-09-08", "event": "Claim approved: $61,500 after $2,500 deductible and depreciation on barn"},
      {"date": "2024-09-12", "event": "Payment issued"}
    ]
  },
  {
    "id": "CLM-2025-0042",
    "client_id": "CLI-1007",
    "policy_id": "POL-CA-2024-002",
    "carrier": "EMC Insurance",
    "type": "commercial_auto",
    "peril": "collision",
    "date_of_loss": "2025-01-15",
    "date_reported": "2025-01-15",
    "status": "open",
    "description": "Company truck (unit 7, 2021 Freightliner Cascadia) jackknifed on I-80 near Kearney during ice storm. Driver Randy Becker Jr. Minor injuries — treated and released at CHI Good Samaritan. Truck towed to TA Petro in Kearney. Trailer load of farm equipment — shipper notified. DOT report filed.",
    "adjuster": {"name": "Julie Kimball", "phone": "(515) 555-7890", "email": "jkimball@emcins.com"},
    "estimated_damage": 45000,
    "police_report": true,
    "police_report_number": "NSP-2025-00412",
    "injuries": true,
    "injury_description": "Driver — bruised ribs, minor lacerations. Treated at CHI Good Samaritan, Kearney. Released same day.",
    "photos_submitted": true,
    "timeline": [
      {"date": "2025-01-15", "event": "FNOL submitted by agency. Flagged high priority — injuries and commercial vehicle."},
      {"date": "2025-01-15", "event": "Adjuster assigned within 2 hours"},
      {"date": "2025-01-16", "event": "Adjuster inspected vehicle at TA Petro Kearney"},
      {"date": "2025-01-17", "event": "Cargo claim opened separately under motor truck cargo policy"}
    ]
  }
]
```

### 2.6 RAG Documents (replace existing docs/)

Remove all existing Octank policy documents. Create new documents that reflect what a Nebraska agency would actually have:

1. **agency_procedures_fnol.md** — Prairie Shield's internal FNOL procedures. How CSRs should handle incoming claims, what to ask, what to document, carrier notification requirements, Nebraska-specific requirements.

2. **carrier_fnol_requirements.md** — Summary of each carrier's specific FNOL requirements, what fields they need, timeframes for reporting, contact info.

3. **nebraska_claims_regulations.md** — Key Nebraska DOI regulations relevant to claims handling. Prompt reporting requirements, unfair claims practices act provisions, timeframes.

4. **coverage_quick_reference.md** — Quick reference for common coverage questions: what's covered under HO3 vs HO5, auto liability vs full coverage, commercial GL basics, farm/ranch specific coverages.

5. **emergency_procedures.md** — What to do for catastrophic losses, after-hours claims, situations involving injuries, when to escalate to the agency principal.

6. **coi_procedures.md** — Certificate of Insurance issuance procedures, additional insured requirements, common mistakes to avoid.

Write each document in 800-1200 words with clear sections. Make them realistic — use the kind of language and detail an actual agency procedures manual would contain.

---

## Phase 3: Core FNOL Automation Engine

### 3.1 Email Intake Parser (NEW: email_parser.py)

Create a new agent that handles the primary intake channel — email. In the demo, we simulate emails arriving. In production, this would monitor an inbox.

**System prompt for the email parser agent:**
```
You are an insurance claims intake specialist at Prairie Shield Insurance Group in Omaha, Nebraska. Your job is to parse incoming emails that report insurance claims (First Notice of Loss) and extract structured data.

From the email, extract:
- Reporter name and contact info
- Policy number (if mentioned)
- Client name (if different from reporter)
- Date of loss (exact or approximate)
- Time of loss (if mentioned)
- Location of loss (specific address or description)
- Type of loss (auto collision, auto comprehensive, homeowners, commercial property, farm/ranch, workers comp, general liability)
- Description of what happened
- Injuries (yes/no, description if yes)
- Police/fire report filed (yes/no, report number if available)
- Other parties involved (names, insurance info if provided)
- Photos or documents mentioned/attached
- Urgency indicators (ongoing damage, injuries, commercial vehicle, livestock)

If critical information is missing, flag it specifically. Always flag:
- Missing policy number (CRITICAL — cannot proceed without it)
- Missing date of loss (CRITICAL)
- Ambiguous loss type
- Any mention of injuries (auto-escalate priority)

Output your extraction as structured JSON matching the FNOLExtraction schema.
```

**FNOLExtraction Pydantic model:**
```python
class FNOLExtraction(BaseModel):
    reporter_name: str
    reporter_email: str | None
    reporter_phone: str | None
    client_name: str | None  # if different from reporter
    policy_number: str | None
    date_of_loss: str | None  # ISO format
    time_of_loss: str | None
    location: str | None
    loss_type: str | None  # enum: auto_collision, auto_comprehensive, homeowners_property, homeowners_liability, commercial_property, commercial_auto, farm_ranch, workers_comp, general_liability, unknown
    description: str
    injuries: bool | None
    injury_description: str | None
    police_report: bool | None
    police_report_number: str | None
    other_parties: list[dict] | None
    photos_mentioned: bool
    attachments: list[str]
    urgency: str  # normal, elevated, high, critical
    missing_fields: list[str]  # fields that need follow-up
    confidence_score: float  # 0.0 to 1.0
    raw_email_text: str
```

### 3.2 FNOL Specialist Agent (rewrite fnol.py)

The existing FNOL agent does guided multi-turn claim filing via chat. Keep that capability but add:

1. **Email-to-FNOL mode**: Takes the FNOLExtraction output from the email parser, enriches it with policy lookup data, validates completeness, and produces a carrier-ready submission.

2. **Interactive mode**: The existing chat-based guided filing, but with updated prompts for Nebraska-specific scenarios and multi-line support (auto, home, farm, commercial).

3. **Missing info follow-up**: When the extraction has gaps, generate a follow-up email to the reporter requesting the specific missing information.

**Updated system prompt for FNOL specialist:**
```
You are a claims filing specialist at Prairie Shield Insurance Group, an independent insurance agency in Omaha, Nebraska. You help process First Notice of Loss (FNOL) claims.

When processing a claim:
1. Verify the policy is active and the date of loss falls within the policy period
2. Confirm the type of loss is potentially covered under the policy
3. Identify the correct carrier and their specific FNOL requirements
4. Format the claim data according to the carrier's submission requirements
5. Flag any coverage concerns (e.g., loss type might not be covered, deductible info)
6. Draft the carrier submission
7. Draft the client confirmation email

Nebraska-specific considerations:
- Nebraska is a fault state for auto accidents
- Hail and wind claims are extremely common — have specific procedures
- Farm/ranch claims may involve livestock — always ask about animal welfare
- Winter claims frequently involve frozen pipes and ice damage
- Prompt reporting to carrier is critical — most require notification within 24-48 hours
- Nebraska DOI requires fair claims handling practices per Neb. Rev. Stat. § 44-1536 through § 44-1544

Priority escalation rules:
- Any injury → HIGH priority, notify agency principal
- Commercial vehicle accident → HIGH priority
- Livestock involved → ELEVATED priority
- Ongoing damage (active water leak, fire) → CRITICAL priority, immediate carrier notification
- Workers comp claim → HIGH priority, OSHA reporting may be required

You have access to the following tools:
- lookup_policy: Look up policy details by policy number or client name
- lookup_client: Look up client information
- get_carrier_requirements: Get the FNOL requirements for a specific carrier
- create_fnol_record: Create a new FNOL record in the agency management system
- generate_carrier_submission: Format the claim for carrier submission
- generate_client_email: Draft a confirmation email to the client
- search_knowledge_base: Search agency procedures and reference documents
```

### 3.3 Policy Lookup Agent (rename eligibility.py → policy_lookup.py)

Repurpose the eligibility agent to do policy verification:

**Tools:**
```python
def lookup_policy(policy_number: str) -> dict:
    """Look up a policy by number. Returns full policy details including
    coverage, carrier, status, effective dates, and client info."""

def lookup_client(client_name: str) -> dict:
    """Look up a client by name (fuzzy match). Returns client details
    and all associated policies."""

def verify_coverage(policy_id: str, date_of_loss: str, loss_type: str) -> dict:
    """Verify that a specific loss type is potentially covered under
    a policy as of the date of loss. Returns coverage details, applicable
    deductible, and any coverage concerns."""
```

### 3.4 Carrier Routing and Submission (NEW: carriers/router.py)

```python
class CarrierRouter:
    """Routes FNOL submissions to the correct carrier with the correct format."""

    def get_carrier_for_policy(self, policy_id: str) -> CarrierInfo:
        """Look up which carrier insures this policy."""

    def get_required_fields(self, carrier_id: str, loss_type: str) -> list[str]:
        """Get the required FNOL fields for this carrier and loss type."""

    def validate_submission(self, carrier_id: str, fnol_data: dict) -> ValidationResult:
        """Check if the FNOL data meets the carrier's requirements. Returns
        list of missing/invalid fields."""

    def format_submission(self, carrier_id: str, fnol_data: dict, policy_data: dict) -> CarrierSubmission:
        """Format the FNOL data into the carrier's required submission format.
        Returns a structured submission object with all fields populated."""

    def generate_acord_form_data(self, fnol_data: dict, policy_data: dict) -> dict:
        """Generate data formatted for ACORD form fields. Many carriers
        accept ACORD standard forms."""
```

### 3.5 Document Generation (NEW: tools/document_generator.py)

Generate two key outputs:

1. **Carrier submission draft** — formatted per carrier requirements, ready for CSR review
2. **Client confirmation email** — professional email confirming receipt, next steps, and what to expect

```python
def generate_carrier_submission(fnol_data: FNOLRecord, policy_data: Policy, carrier: CarrierInfo) -> str:
    """Use Claude to generate a properly formatted carrier FNOL submission.
    Output should match the carrier's expected format (ACORD, custom form, email body)."""

def generate_client_confirmation(fnol_data: FNOLRecord, client: Client, carrier: CarrierInfo) -> str:
    """Generate a professional, empathetic client confirmation email.
    Include: claim reference number, carrier name, what to expect next,
    adjuster timeline, what the client should do (get repair estimates,
    don't dispose of damaged property, take photos), agency contact info."""

def generate_followup_email(fnol_extraction: FNOLExtraction, missing_fields: list[str]) -> str:
    """Generate a polite follow-up email requesting missing information
    needed to complete the FNOL filing."""
```

---

## Phase 4: Frontend Redesign

### 4.1 New Screen Flow

Replace the 4-screen layout (Auth → Chat → Agent Desktop → Analytics) with:

**Screen 1: Dashboard**
The main screen. Shows:
- Incoming claims queue (email cards with status: new, processing, needs review, submitted)
- Quick stats: claims today, average processing time, pending reviews
- Recent activity feed

**Screen 2: Claim Processing View**
When a claim is selected from the queue:
- Left panel: Original email/intake (raw text, any attachments listed)
- Center panel: AI-extracted FNOL data in an editable form. Fields are pre-filled by AI with confidence indicators (green = high confidence, yellow = medium, red = low/missing). CSR can edit any field.
- Right panel: AI Transparency panel (carried over from existing Under the Hood, showing agent trace, tools called, RAG sources used, confidence breakdown)
- Bottom bar: Action buttons — "Approve & Submit to Carrier", "Send Follow-up Email", "Save as Draft", "Escalate to Agent"

**Screen 3: Carrier Submission Preview**
After approval, shows:
- The formatted carrier submission (what will be sent)
- Client confirmation email (what the client will receive)
- Side-by-side with edit capability
- "Submit" button (in demo, just marks as submitted and shows success)

**Screen 4: Agent Desktop (keep existing, modified)**
For escalated claims that need human handling:
- Keep the existing 4-panel layout (screen pop, transcript, knowledge, agent assist)
- Update the AI summary to reflect insurance context
- Update knowledge panel to use insurance RAG docs

### 4.2 Design System

- Clean, professional, light mode (not the existing dark mode — agency owners expect business software aesthetics)
- Color palette: Deep blue primary (#1B3A5C), white background, light gray panels (#F5F7FA), green for success/approved (#2D8A4E), amber for warnings (#D4930D), red for critical (#C4342D)
- Typography: Inter or system fonts. No fancy fonts.
- Card-based layout with subtle shadows
- The overall feel should be "modern business SaaS" — think something between Salesforce and a clean startup product. Not flashy, not dated.

### 4.3 Demo Flow / Quick Actions

Replace existing quick action buttons with insurance-specific demo scenarios:

1. **"New Email Claim — Auto Accident"** — Simulates receiving an email from Tom Rezac about a fender bender. Shows the full pipeline: email → extraction → policy lookup → carrier submission → client confirmation.

2. **"New Email Claim — Hail Damage"** — Simulates a hail damage claim from Linda Sorensen. Demonstrates homeowners workflow with property-specific details.

3. **"New Email Claim — Farm Loss"** — Simulates a farm claim from Jim Schroeder. Shows farm/ranch-specific handling including livestock concerns.

4. **"New Email Claim — Commercial Vehicle"** — Simulates a trucking accident from Great Plains Trucking. Demonstrates high-priority commercial workflow with injury flagging.

5. **"Incomplete Claim"** — Simulates an email with missing critical info. Shows the AI identifying gaps and generating a follow-up email.

6. **"Check Claim Status"** — Interactive chat where a client asks about an existing claim. Uses the claims status agent.

Each quick action should pre-load a realistic email and kick off the full processing pipeline with the observability panel showing each step.

### 4.4 Sample Emails for Demo Scenarios

Pre-write realistic emails for each demo scenario. These should feel like actual emails an agency receives.

**Auto Accident Email:**
```
From: tom.rezac@email.com
To: claims@prairieshield.com
Subject: Car accident this morning

Hi Lisa,

I was in an accident this morning on my way to work. I was stopped at the light at 72nd and Dodge and someone ran the red light and rear-ended me. Pretty hard hit. My truck (the F-150) has bumper damage and the tailgate won't close properly. I think the frame might be bent too.

The other driver's name is Maria Gonzales, she has State Farm. I got her info and the police came and made a report. I can get you the report number once they file it — the officer said it would be available in a couple days. OPD case number is 2024-889431.

No one was hurt thankfully, just shook up. The truck is still drivable but it doesn't feel right.

My policy number is AO-PA-8847321.

Let me know what I need to do next.

Thanks,
Tom
```

**Hail Damage Email:**
```
From: linda.sorensen@outlook.com
To: claims@prairieshield.com
Subject: Hail damage from last night's storm

Mark,

We got hit hard with that storm last night. The hail was huge — bigger than golf balls. Started around 9:30 PM and went on for maybe 20 minutes.

The roof is definitely damaged, I can see broken shingles from the ground and there's some in the yard. The siding on the north side of the house has dents everywhere. Both skylights in the upstairs bathroom are cracked and I'm worried about leaking if it rains again.

The gutters on the east side are smashed too. My neighbor said his adjuster told him the whole neighborhood is going to need roofs.

I took some pictures this morning, I can email those over. Should I get a roofer out for an estimate or wait for the insurance adjuster?

My husband and I are just sick about it. That roof was only 5 years old.

Linda Sorensen
Policy: I don't have it in front of me but you should have it on file
912 W 4th St, Grand Island
(308) 555-0123
```

**Farm Loss Email:**
```
From: schroeder.farm@yahoo.com
To: claims@prairieshield.com
Subject: Storm damage — barn and grain bins

Mark, it's Jim Schroeder calling — well, emailing. Nancy said I should email you so there's a record.

We had severe storms come through yesterday evening around 6 PM. Straight-line winds, the weather service said 70-80 mph. The north barn — the older one, not the new steel building — the west wall caved in and part of the roof came down. That barn still had some hay and a couple pieces of older equipment in it.

Two of the grain bins are dented pretty bad. One of them the roof is pushed in and I don't know if it's going to hold. They're empty right now thank god but harvest is coming.

Also lost about 400 feet of fence along Highway 81. A dozen head got out but the neighbors helped us round them all up. Everyone's accounted for, cattle are fine.

No one was hurt. Just a hell of a mess out here.

Our policy number is GM-FR-NE-445672. This is through Grinnell Mutual I believe.

Call me when you get a chance. I'll be out here all day cleaning up.

Jim
402-555-0512
```

**Commercial Vehicle Email:**
```
From: dispatch@gptrucking.com
To: claims@prairieshield.com
Subject: URGENT — Truck accident on I-80 near Kearney

Mark,

We need to file a claim immediately. One of our trucks jackknifed on I-80 just west of Kearney this afternoon around 2 PM. The roads were icy and the rig went sideways.

Driver is Randy Becker Jr. He's okay but went to the hospital in Kearney (Good Samaritan) to get checked out. They're saying bruised ribs and some cuts. He's been released.

The truck is a 2021 Freightliner Cascadia, unit 7. It's been towed to the TA truck stop in Kearney. Trailer was loaded with farm equipment heading to a dealer in Denver — I need to call the shipper about the cargo.

Nebraska State Patrol was on scene. Report number is NSP-2025-00412.

This is on our commercial auto policy with EMC, policy number EMC-CA-BZ-224891.

Please get this to the carrier ASAP. With the injury involved I know they'll want to get on it quick.

Randy Becker Sr.
Great Plains Trucking
(402) 555-0945
```

**Incomplete Claim Email:**
```
From: mtorres84@gmail.com
To: claims@prairieshield.com
Subject: my car got broken into

Hi I need to file a claim. Someone broke into my car last night and stole a bunch of stuff. They smashed the back window. This happened at my apartment on Vinton Street.

Can you help me with this?

Miguel
```

---

## Phase 5: Supervisor Agent Updates

### 5.1 Updated Intent Classification

Modify the supervisor agent to classify insurance-specific intents:

```python
INTENT_CATEGORIES = [
    "fnol_auto",            # Auto accident/damage claim
    "fnol_property",        # Home/commercial property damage claim
    "fnol_farm",            # Farm/ranch loss claim
    "fnol_commercial",      # Commercial liability/vehicle claim
    "fnol_workers_comp",    # Workers compensation claim
    "claim_status",         # Check on existing claim
    "policy_question",      # Coverage question, policy lookup
    "coi_request",          # Certificate of insurance request
    "billing_question",     # Payment, premium question
    "general",              # General inquiry
    "escalate"              # Wants to talk to a human
]
```

### 5.2 Priority Classification

Add priority classification to the supervisor:

```python
PRIORITY_LEVELS = [
    "critical",     # Ongoing damage, injuries requiring medical attention, fire
    "high",         # Injuries (minor), commercial vehicle, workers comp, livestock
    "elevated",     # Large loss estimate, multiple vehicles, time-sensitive
    "normal"        # Standard FNOL filing
]
```

The supervisor should output both intent and priority in a single classification pass.

---

## Phase 6: Guardrails Updates

### 6.1 Insurance-Specific Guardrails

Extend the existing guardrails with insurance-specific rules:

```python
# Coverage opinion blocking
# The AI must NEVER state definitively that something is or isn't covered.
# It can say "this type of loss is typically covered under your policy type"
# but must always defer to the carrier's determination.
BLOCKED_PHRASES = [
    "this is covered",
    "this is not covered",
    "your claim will be approved",
    "your claim will be denied",
    "you are entitled to",
    "the carrier must pay",
    "you should receive"
]

# Always append to coverage-related responses:
COVERAGE_DISCLAIMER = "Please note that all coverage determinations are made by your insurance carrier. This information is provided for reference only and does not constitute a coverage opinion."

# PII handling — extend existing
# Insurance claims contain lots of PII. The system should process it
# (it needs names, addresses, etc.) but should never log full SSNs,
# driver's license numbers, or financial account numbers.
# Redact in logs/traces but allow in the actual FNOL processing.

# Nebraska-specific compliance flags
# Flag if claim is reported more than 48 hours after date of loss (carrier prompt reporting requirements)
# Flag if injuries are mentioned (may trigger additional reporting requirements)
# Flag if commercial vehicle over 10,001 lbs (DOT/FMCSA reporting)
# Flag workers comp claims (OSHA reporting, NE Workers' Compensation Court)
```

---

## Phase 7: API Routes

### 7.1 Updated/New Endpoints

```python
# Keep existing
GET  /api/health
GET  /api/members → rename to /api/clients
POST /api/session/start
GET  /api/session/{id}
POST /api/chat
WS   /ws/{id}

# Modify
GET  /api/agent-desktop/{id}  → Update for insurance context

# New
POST /api/claims/intake           # Submit an email for FNOL processing
GET  /api/claims                  # List all claims
GET  /api/claims/{id}             # Get claim details
POST /api/claims/{id}/approve     # Approve AI extraction, trigger submission generation
POST /api/claims/{id}/submit      # "Submit" to carrier (mock — marks as submitted)
GET  /api/claims/{id}/submission  # Get the formatted carrier submission
GET  /api/claims/{id}/client-email # Get the draft client confirmation email
POST /api/claims/{id}/followup   # Generate follow-up email for missing info

GET  /api/policies                # List policies
GET  /api/policies/{id}           # Get policy details
GET  /api/policies/search?q=      # Search by policy number, client name

GET  /api/carriers                # List carriers
GET  /api/carriers/{id}           # Get carrier details and FNOL requirements

POST /api/demo/scenario/{name}    # Trigger a demo scenario (loads pre-written email + processes it)
```

### 7.2 WebSocket Events

Extend the existing WebSocket trace events to include the new pipeline stages:

```python
TRACE_EVENTS = [
    "email_received",           # New email arrived
    "parsing_started",          # Email parser agent invoked
    "extraction_complete",      # Structured data extracted
    "policy_lookup_started",    # Looking up policy in AMS
    "policy_verified",          # Policy found and verified
    "coverage_check_complete",  # Coverage verification done
    "carrier_identified",       # Carrier for this policy identified
    "carrier_requirements_loaded",  # Carrier's FNOL requirements loaded
    "validation_complete",      # FNOL data validated against carrier requirements
    "missing_fields_flagged",   # Missing info identified
    "submission_generated",     # Carrier submission formatted
    "client_email_generated",   # Client confirmation drafted
    "priority_assigned",        # Priority level set
    "guardrails_passed",        # Guardrails checks complete
    "ready_for_review",         # Claim ready for human review
    "escalated"                 # Claim auto-escalated
]
```

---

## Phase 8: Testing and Demo Polish

### 8.1 Demo Script

Create a `DEMO_SCRIPT.md` file with:

1. **Setup instructions** — how to start the server, expected environment
2. **Walkthrough script** — step-by-step guide for presenting to an agency owner:
   - Start on the dashboard showing an empty queue
   - Trigger the auto accident scenario
   - Watch the email arrive and get processed in real-time
   - Show the AI transparency panel as it works
   - Review the extracted data, show confidence scores
   - Approve and show the carrier submission + client email
   - Then trigger the incomplete claim to show the follow-up flow
   - Then trigger the farm loss to show multi-line capability
   - End with the chat interface for claim status lookup
3. **Talking points** — what to say at each step, anticipated questions from agency owners, objections and responses

### 8.2 Performance Targets

- Email-to-extraction: < 5 seconds
- Full pipeline (email → submission draft): < 15 seconds
- Chat response time: < 3 seconds
- UI should feel responsive — show processing states, streaming indicators

### 8.3 Error Handling

- If Anthropic API fails: Show a clean error state, not a crash
- If policy lookup fails (policy not in mock data): AI should say "I couldn't find that policy number in our system. Let me flag this for manual lookup."
- If carrier isn't in our mock data: Default to generic ACORD format submission

---

## Phase 9: Future Features (Stub Out, Don't Build Yet)

Leave placeholder UI elements and backend stubs for these. They show the agency owner the product roadmap and create upsell opportunities. Mark them as "Coming Soon" in the UI.

1. **COI Generation** — Certificate of Insurance automation. Stub the UI button and the agent file.
2. **Renewal Processing** — Automated renewal monitoring and comparison. Stub a "Renewals" tab on the dashboard.
3. **Loss Run Analysis** — PDF ingestion and analysis. Stub an "Upload Loss Runs" button.
4. **AMS Integration Settings** — Settings page with dropdown for AMS selection (Applied Epic, Hawksoft, AMS360, QQ Catalyst) and mock connection flow. Shows the agency owner it's designed to plug into their existing system.
5. **Carrier Portal Integrations** — Settings showing carrier connections with status indicators (Connected, Available, Coming Soon).
6. **Reporting** — Claims volume, processing time trends, cost savings calculator. Stub a "Reports" tab.

---

## Implementation Priority Order

Build in this order to have a demo-ready product as fast as possible:

1. **Phase 1** (rebrand, restructure, switch to Anthropic API) — Foundation
2. **Phase 2** (mock data) — Create all JSON data files
3. **Phase 3.1-3.2** (email parser + FNOL specialist) — Core AI engine
4. **Phase 3.3** (policy lookup) — Quick repurpose of existing agent
5. **Phase 4.1-4.2** (frontend dashboard + claim processing view) — Main UI
6. **Phase 3.4-3.5** (carrier routing + document generation) — Submission pipeline
7. **Phase 4.3-4.4** (demo scenarios + sample emails) — Demo polish
8. **Phase 5** (supervisor updates) — Classification improvements
9. **Phase 6** (guardrails) — Compliance layer
10. **Phase 7** (API routes) — Wire everything together
11. **Phase 8** (testing + demo script) — Final polish
12. **Phase 9** (stubs) — Future feature placeholders

---

## Key Technical Decisions

- **Use Claude Sonnet 4 for everything** — Don't split Haiku/Sonnet. For a demo product, consistent quality matters more than cost optimization. Optimize for cost later.
- **Keep sessions in-memory** — No database. This is a demo. Add persistence when selling to a real agency.
- **Mock all external integrations** — AMS APIs, carrier portals, email ingestion. Return realistic mock data. The integration layer is where real consulting revenue comes from — sell the demo, then get paid to build the integrations.
- **Vanilla JS frontend** — Keep it. No React/Vue. The existing codebase is already vanilla and it works. Don't introduce a build step for a demo.
- **Keep the observability panel** — Rename it "AI Transparency." Agency owners are nervous about AI. Showing them exactly what the AI is doing, what tools it called, what documents it referenced, and how confident it is builds trust. This is a differentiator.
- **Human-in-the-loop is mandatory** — The AI never submits anything without human review. Every output is a draft that the CSR approves. This is non-negotiable for insurance. Emphasize this in the UI and the demo script.

---

## Environment Setup

```bash
# .env.example
ANTHROPIC_API_KEY=sk-ant-...
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=info

# Model config
MODEL=claude-sonnet-4-20250514
MAX_TOKENS=4096
TEMPERATURE=0.1

# RAG config
RAG_CHUNK_SIZE=500
RAG_CHUNK_OVERLAP=100
RAG_TOP_K=4

# Session config
SESSION_TIMEOUT_MINUTES=60
```

```bash
# start.sh
#!/bin/bash
cd "$(dirname "$0")"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --host ${HOST:-0.0.0.0} --port ${PORT:-8000} --reload
```

```
# requirements.txt
anthropic>=0.40.0
fastapi>=0.110.0
uvicorn[standard]>=0.27.0
pydantic>=2.5.0
scikit-learn>=1.3.0
python-dotenv>=1.0.0
websockets>=12.0
python-multipart>=0.0.6
```

---

## Success Criteria

The demo is ready when:

1. An agency owner can watch the auto accident email arrive and see it processed into a carrier-ready submission in under 15 seconds
2. The extracted data is accurate and the form is editable
3. The carrier submission looks professional and matches what they'd manually create
4. The client confirmation email is empathetic and informative
5. The incomplete claim scenario clearly shows the AI identifying missing info and generating a follow-up
6. The farm claim scenario demonstrates multi-line capability with Nebraska-specific concerns (livestock, grain bins)
7. The commercial vehicle scenario shows priority escalation for injuries
8. The claim status chat works for checking existing claims
9. The AI transparency panel shows every step clearly
10. The overall UI feels like a real SaaS product, not a hackathon project
