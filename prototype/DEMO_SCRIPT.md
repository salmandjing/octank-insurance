# ClaimFlow AI -- Demo Script

A step-by-step walkthrough for demonstrating ClaimFlow AI to an insurance agency owner. This script uses Prairie Shield Insurance Group in Omaha, NE as the demo agency.

**Demo duration**: 20-30 minutes
**Audience**: Agency owner/principal, operations manager, or senior CSR
**What you need**: A laptop with the application running, an internet connection (for the Anthropic API), and a browser open to http://localhost:8000

---

## 1. Setup

### Prerequisites

- Python 3.11 or later installed
- An Anthropic API key (starts with `sk-ant-api03-`)

### Starting the Application

```bash
cd prototype
cp .env.example .env
```

Edit `.env` and paste your Anthropic API key:

```
ANTHROPIC_API_KEY=sk-ant-api03-YOUR-KEY-HERE
```

Start the server:

```bash
chmod +x start.sh
./start.sh
```

You should see:

```
ClaimFlow AI -- FNOL Automation for Agencies
Anthropic API key configured
Starting ClaimFlow AI on http://localhost:8000
```

Open **http://localhost:8000** in Chrome. You should see the ClaimFlow AI dashboard with the Prairie Shield Insurance Group header and five demo scenario buttons.

### Pre-Demo Checklist

- [ ] Application is running and the dashboard loads cleanly
- [ ] Stats bar shows zeros (fresh state, no claims processed yet)
- [ ] Claims Queue shows "No claims yet. Use a demo scenario to get started."
- [ ] Chat panel is visible in the bottom-right corner
- [ ] Run one scenario privately beforehand to confirm API connectivity, then restart the server to reset state

---

## 2. Opening Pitch

Start the conversation before touching the keyboard. Set the stage for why this exists.

**What to say:**

> "Let me show you something we've been building specifically for independent agencies like yours. The biggest time sink in your office right now -- and tell me if I'm wrong -- is FNOL intake. A client calls or emails about an accident, and your CSR spends 30 to 60 minutes on each claim: pulling up the policy, typing everything into the carrier's portal, sending the client a confirmation, making sure nothing got missed. Multiply that by the number of claims you process in a week.
>
> What ClaimFlow AI does is automate the intake-to-submission pipeline. An email comes in, the AI reads it, pulls the policy, identifies the carrier, and drafts everything -- the carrier submission, the client confirmation email, all of it. Your CSR reviews it, makes any edits, and clicks submit. The AI never submits anything on its own. Your people are always in the loop. It just does the grunt work so they can focus on the client relationship.
>
> Let me walk you through it with some real scenarios."

**If they ask how long it takes:** "Email to submission-ready in under 15 seconds. Let me show you."

**If they ask about carriers:** "We've configured it for the carriers you actually work with -- Auto-Owners, Erie, EMC, Grinnell Mutual, Westfield. Each carrier has different FNOL requirements and the system knows them."

---

## 3. Scenario 1: Auto Accident -- Full Walkthrough

**Client**: Tom Rezac
**What happened**: Rear-ended at 72nd and Dodge in Omaha
**Policy**: Auto-Owners, personal auto (AO-PA-8847321)
**Vehicle**: 2022 Ford F-150 XLT

This is your anchor demo. Walk through every step slowly and explain what is happening.

### Step 1: Trigger the Scenario

**What to say:**

> "So imagine it's Monday morning. Tom Rezac, one of your personal auto clients, just had a fender bender on his way to work. He sends an email to your claims inbox. Let's see what happens."

**What to click:** On the dashboard, click the **"Auto Accident"** demo card (first card, with the car icon).

**What happens:** The system simulates receiving Tom's email and processes it through the AI pipeline. You will see a loading state while the AI works, then you will be taken to the Claim Processing view.

**What to say while it processes:**

> "Right now the AI is reading the email, extracting every piece of structured data it can find -- the client's name, their policy number, when and where it happened, whether there were injuries, whether a police report was filed, who the other driver was. Then it's looking up the policy in your management system, verifying the coverage is active, identifying Auto-Owners as the carrier, and checking their specific FNOL requirements."

### Step 2: Review the Claim Processing View

Once processing completes, you will see a three-column layout:

- **Left panel**: The original email from Tom
- **Center panel**: The AI-extracted FNOL data in an editable form
- **Right panel**: AI Transparency showing the processing trace

**Walk through the left panel:**

> "Here's the raw email exactly as Tom sent it. He's writing to Lisa -- that's his agent -- in plain English. No form, no structure. Just a regular email. This is what your CSRs deal with every day."

**Walk through the center panel (extraction form):**

> "Now look at what the AI pulled out. Reporter name: Tom Rezac. Policy number: AO-PA-8847321 -- it found that in the email. Date of loss, location at 72nd and Dodge, loss type correctly classified as auto collision. The description is structured. It noted that a police report was filed -- OPD case number 2024-889431. No injuries. And it captured the other party: Maria Gonzales with State Farm.
>
> Every one of these fields is editable. If the AI got something wrong or the CSR wants to add detail, they just type in the field. The AI drafts, your people decide."

**Point out the confidence indicators next to each field.** These show how confident the AI is about each extracted value.

**Walk through the right panel (AI Transparency):**

> "This is what we call the AI Transparency panel. Your CSR can see exactly what the AI did -- step by step. It parsed the email, looked up the policy, verified coverage, identified Auto-Owners as the carrier, checked their FNOL requirements, ran compliance checks. Nothing is a black box. If a CSR wants to know why the AI classified this as a collision instead of a comprehensive claim, they can see the reasoning right here."

**Point out the Policy Lookup section** in the right panel:

> "It pulled up the full policy -- Auto-Owners personal auto, active, 100/300/100 liability limits, $500 collision deductible. Your CSR didn't have to open a separate system or look anything up."

### Step 3: Approve and Generate Submission

**What to say:**

> "The CSR has reviewed everything, it all looks good. Now watch what happens when they approve."

**What to click:** Click the **"Approve & Generate Submission"** button in the bottom action bar.

**What happens:** The system generates two documents:
1. A carrier FNOL submission formatted for Auto-Owners (ACORD format)
2. A client confirmation email to Tom

You are taken to the **Submission Preview** screen, which shows both documents side by side.

**Walk through the carrier submission (left side):**

> "This is the carrier submission, formatted the way Auto-Owners expects it. Policy number, insured's information, date and time of loss, location, description, other party details, police report number -- all the required fields filled in. It even includes Prairie Shield as the reporting agency. Your CSR can edit any of this before it goes out."

**Walk through the client email (right side):**

> "And here's the confirmation email to Tom. It's professional, empathetic -- acknowledges his situation, gives him the claim reference number, tells him Auto-Owners will assign an adjuster within 24 hours, reminds him to take photos and get repair estimates. This is what your clients see. It goes out under your agency's name, not some robot."

**Point out that both are editable text areas.** The CSR can modify anything before submitting.

### Step 4: Submit to Carrier

**What to say:**

> "Once the CSR is happy with both documents, one click sends it."

**What to click:** Click the **"Submit to Carrier"** button.

**What happens:** A success confirmation appears. The claim is marked as submitted. In production, this would push to the carrier's portal or email. In this demo, it records the submission and updates the status.

**What to say:**

> "Done. From email to carrier submission in under a minute. That's a process that normally takes your CSR 30 to 45 minutes. And nothing went to the carrier without a human reviewing it first."

**What to click:** Click **"Return to Dashboard"** to go back to the main screen.

**Point out on the dashboard:** The Claims Queue now shows Tom's claim with a "Submitted" status, and the stats bar has updated.

---

## 4. Scenario 2: Hail Damage -- Property Claim

**Client**: Linda Sorensen, Grand Island, NE
**What happened**: Severe hail storm, roof and siding damage
**Policy**: Westfield Insurance, homeowners (WF-HO-4412877)
**Property**: 912 W 4th St, Grand Island

### Step 1: Set the Context

**What to say:**

> "Let's look at a different kind of claim. We're in Nebraska -- hail season is a reality for every agency. After a big storm, you might get 20 or 30 of these in a single day. Let's see how ClaimFlow handles it."

**What to click:** Click the **"Hail Damage"** demo card (second card, with the hail icon).

### Step 2: Review the Extraction

Once processing completes, walk through what the AI found:

> "Linda Sorensen from Grand Island. She didn't even have her policy number handy -- she said 'you should have it on file.' But the AI matched her by name and address to her Westfield homeowners policy. It identified this as a homeowners property claim. It picked up that the roof is damaged, the skylights are cracked, the siding and gutters are damaged. It noted she mentioned photos. And it flagged that there could be ongoing damage -- those cracked skylights could leak -- which means this might need priority handling."

**Key talking points for property claims:**

> "Notice it pulled in her property details from the policy -- the dwelling coverage, the wind/hail deductible. For Westfield, the hail deductible is 2% of the dwelling value, which is different from the standard deductible. That's the kind of detail that can trip up a new CSR, but the system surfaces it automatically."

**If the agency owner mentions hail season volume:**

> "Imagine getting 30 of these after a big storm. Your CSRs are on the phone all day with panicked clients. With ClaimFlow, the emails come in, the AI processes them in parallel, and your team just reviews and approves. You could process a day's worth of hail claims in an hour instead of all day."

### Step 3: Approve and Submit

Follow the same approve-and-submit flow as Scenario 1. Point out that the carrier submission is formatted for Westfield's requirements, which differ from Auto-Owners.

Click **"Return to Dashboard"** when done. The queue now shows two claims.

---

## 5. Scenario 3: Farm Loss -- Multi-Line Claim

**Client**: Jim Schroeder, York, NE
**What happened**: Straight-line winds, 70-80 mph -- barn collapsed, grain bins damaged, fence destroyed, cattle escaped
**Policy**: Grinnell Mutual, farm/ranch (GM-FR-NE-445672)
**Property**: 640-acre farm, Rural Route 2, Box 44, York

### Step 1: Set the Context

**What to say:**

> "Now let's look at something more complex. This is where it gets interesting for a Nebraska agency. Farm and ranch claims are some of the hardest to process because they involve multiple structures, equipment, livestock, and sometimes multiple coverage sections on a single policy. Let me show you a storm damage claim from a farm client."

**What to click:** Click the **"Farm Loss"** demo card (third card, with the barn icon).

### Step 2: Review the Extraction

> "Jim Schroeder, York, Nebraska. 640-acre cattle operation. Straight-line winds took out the older barn, damaged two grain bins, blew down 400 feet of fence, and a dozen head of cattle got out. The AI picked up every one of those loss items from a plain-English email.
>
> Look at the policy data it pulled -- Grinnell Mutual farm/ranch policy. $280,000 dwelling, $262,000 in farm structures, $385,000 in farm personal property, $324,000 in livestock coverage. Three grain bins on the policy. The AI knows this is a multi-structure, multi-peril claim that needs to go to Grinnell Mutual's specific farm loss department.
>
> It also noted the livestock concern -- even though the cattle are all accounted for, any claim involving livestock gets flagged because Grinnell Mutual wants to know about animal welfare immediately."

**Key talking points for farm claims:**

> "This is a claim that would take an experienced CSR an hour or more to process manually, because you're pulling coverage details for the barn, the bins, the fence, the livestock, cross-referencing scheduled equipment values, and formatting all of it for Grinnell's custom farm loss form. The AI handles the complexity."

### Step 3: Approve and Submit

Follow the same approve-and-submit flow. Point out that Grinnell Mutual uses a custom form format instead of the standard ACORD, and the system adapts automatically.

---

## 6. Scenario 4: Commercial Vehicle -- Priority Escalation

**Client**: Great Plains Trucking Inc (Randy Becker Sr., dispatcher)
**What happened**: 2021 Freightliner Cascadia jackknifed on I-80 near Kearney during an ice storm. Driver injured. Cargo involved.
**Policy**: EMC Insurance (EMCASCO), commercial auto (EMC-CA-BZ-331205)

### Step 1: Set the Context

**What to say:**

> "Let's look at a high-priority commercial claim. This is the kind of call that makes a CSR's heart rate go up -- a trucking accident with injuries."

**What to click:** Click the **"Commercial Vehicle"** demo card (fourth card, with the truck icon).

### Step 2: Review the Extraction -- Emphasize Priority

> "Notice the priority badge immediately -- this is flagged as HIGH priority. The AI detected two escalation triggers: injuries reported and commercial vehicle involved. In your office, this would go to the top of the queue.
>
> The AI extracted everything: the driver's name, Randy Becker Jr., the fact that he went to Good Samaritan hospital with bruised ribs and cuts, the truck details -- unit 7, 2021 Freightliner Cascadia -- towed to the TA Petro in Kearney. The Nebraska State Patrol report number. The cargo information -- farm equipment heading to Denver. And it correctly identified this needs to go to EMC on their commercial auto policy.
>
> It also flagged that there may be a separate cargo claim needed under the motor truck cargo policy. That's the kind of thing an AI catches that a rushed CSR might miss on a Monday morning."

**Key talking points for commercial claims:**

> "With injuries involved, EMC wants this reported immediately. The system knows that and flags it. In production, this would trigger an alert to the agency principal and prioritize it above everything else in the queue.
>
> Also notice the compliance flags -- with a commercial vehicle over 10,001 pounds, there may be DOT and FMCSA reporting requirements. The system surfaces that so nothing falls through the cracks."

### Step 3: Approve and Submit

Follow the same approve-and-submit flow. Emphasize the speed:

> "From a panicked dispatch call to a carrier submission in under a minute. For a commercial claim with injuries, that response time matters -- for the driver, for the carrier relationship, and for your E&O exposure."

---

## 7. Scenario 5: Incomplete Claim -- Follow-Up Workflow

**Client**: Miguel Torres, Omaha
**What happened**: Car broken into overnight, window smashed, items stolen
**Policy**: Auto-Owners, personal auto (AO-PA-9912345)

### Step 1: Set the Context

**What to say:**

> "Not every email that comes in has all the information you need. Let's look at what happens when a client sends something incomplete."

**What to click:** Click the **"Incomplete Claim"** demo card (fifth card, the one with the warning icon).

### Step 2: Review the Extraction -- Show the Gaps

> "Miguel Torres sent a short email: 'someone broke into my car and stole a bunch of stuff, smashed the back window, happened at my apartment on Vinton Street.' That's it. No policy number, no date, no police report, no list of what was stolen.
>
> Look at how the AI handled it. It identified Miguel by his email address and pulled up his client record. It classified this as an auto comprehensive claim. But look at the missing fields -- no specific date of loss, no police report number, no detailed description of what was stolen, no estimated value. The confidence score is lower because of the gaps.
>
> This claim can't go to the carrier yet. It's not ready."

### Step 3: Generate Follow-Up Email

**What to say:**

> "Instead of the approve button, notice the system is showing a **Send Follow-up Email** button. Watch what it generates."

**What to click:** Click the **"Send Follow-up Email"** button in the bottom action bar.

**What happens:** The AI generates a professional, friendly follow-up email to Miguel listing exactly what information is still needed and why.

> "The AI drafted a follow-up email to Miguel. It thanks him for reporting the claim, then lists exactly what we still need: the specific date and time it happened, whether he filed a police report, a list of the stolen items with approximate values, and any photos of the damage. It explains why each piece matters -- the police report for the carrier, the item list for the claim valuation.
>
> Your CSR reviews this email, edits it if needed, and sends it. When Miguel replies with the missing info, it comes back through the pipeline and picks up where it left off."

**Key talking point:**

> "This is where the AI really saves your team time. Writing a polite, professional follow-up email that lists exactly what's needed -- that's 10-15 minutes of a CSR's time for every incomplete claim. Multiply that by how many incomplete claims you get in a week."

---

## 8. Chat Demo: Claim Status and Policy Questions

The chat panel sits in the bottom-right corner of the screen and is always available.

### Step 1: Open the Chat

**What to click:** Click the **"ClaimFlow Assistant"** chat header at the bottom-right of the screen to expand the chat panel.

**What to say:**

> "In addition to processing incoming claims, ClaimFlow has an interactive assistant for your CSRs. They can ask questions about claims, policies, or procedures right from the dashboard."

### Step 2: Ask About a Claim Status

**What to type in the chat input:**

```
What's the status of the hail damage claim for Linda Sorensen?
```

**What to say after the response:**

> "The assistant pulled up Linda's claim and gave the status, the carrier, the timeline of what's happened so far. If a client calls asking about their claim, your CSR gets the answer in seconds without switching systems."

### Step 3: Ask a Policy Question

**What to type in the chat input:**

```
Does Tom Rezac's auto policy have uninsured motorist coverage?
```

**What to say after the response:**

> "It looked up Tom's policy and gave the coverage details. $100,000/$300,000 uninsured motorist limits. Your CSR didn't have to open the AMS, find the policy, navigate to the coverage page. They just asked."

### Step 4: Ask a General Insurance Question

**What to type in the chat input:**

```
What are Nebraska's prompt reporting requirements for FNOL?
```

**What to say after the response:**

> "It searched the knowledge base -- your agency's own procedures and reference documents -- and gave an answer grounded in your actual documentation. This is like having your procedures manual available as a conversation."

**Key talking points for chat:**

> "The assistant is backed by the same AI and the same data. It knows your clients, your policies, your carriers, and your procedures. For a new CSR who's still learning the ropes, this is like having a senior agent sitting next to them. For an experienced CSR, it just saves time."

---

## 9. Closing -- Return to Dashboard, ROI Discussion

**What to click:** Navigate back to the dashboard.

**What to say, gesturing at the Claims Queue:**

> "We just processed five claims in about 15 minutes, including a complex farm loss and a commercial vehicle accident with injuries. In a traditional workflow, those five claims would have taken your CSRs somewhere between 2.5 and 5 hours of combined processing time.
>
> Let me leave you with a few numbers."

### Time Savings

> "The average FNOL takes a CSR 30 to 60 minutes. ClaimFlow gets it to review-ready in under 15 seconds. Even with your CSR spending 5 minutes reviewing and approving, you're saving 25 to 55 minutes per claim. If you're processing 10 claims a day, that's 4 to 9 hours of CSR time recovered every single day."

### Accuracy and Compliance

> "The AI doesn't miss fields. It checks every carrier's specific requirements before the submission goes out. It flags compliance issues -- late reporting, injury notifications, DOT requirements. The number of claims that get kicked back by the carrier for missing information drops dramatically."

### The Human-in-the-Loop Promise

> "I want to be clear about something: the AI never submits anything. Everything it produces is a draft. Your CSR reviews every extraction, edits any field they want, and approves before anything goes to the carrier or the client. This is an augmentation tool, not a replacement. Your people are still running the show -- they're just doing it faster."

### What This Connects To

> "What you're seeing today runs standalone, but it's designed to plug into your existing AMS -- whether that's Applied Epic, Hawksoft, AMS360, or QQ Catalyst. The carrier connections you saw are mock right now, but the integration layer maps directly to each carrier's real portal or API. We build those integrations for your specific setup."

### Coming Soon (point at the UI badges)

> "You'll notice a few things labeled 'Coming Soon' in the interface -- COI generation, renewals monitoring, reporting. Those are in the roadmap. The FNOL automation is the foundation, and once it's in place, those add-ons build on top of it."

### Close

> "The bottom line: your CSRs spend less time on data entry and more time talking to clients. Your claims get to the carrier faster, which means faster adjuster assignment and faster resolution for your clients. And you get a compliance trail for every claim that came through the system.
>
> What questions do you have?"

---

## 10. Anticipated Questions and Responses

**"What if the AI gets something wrong?"**
> "That's exactly why the human review step is mandatory. The AI does its best to extract and structure the data, but the CSR always reviews and can edit any field before approval. Think of it as a really fast first draft. The confidence scores help too -- if the AI isn't sure about something, it tells you."

**"What about sensitive client data?"**
> "The system processes the data it needs to do its job -- names, addresses, policy numbers. But it's designed with PII handling in mind. Social Security numbers, driver's license numbers, and financial account numbers are redacted in system logs. The data stays on your infrastructure -- it's not stored in any third-party system."

**"How does it handle carriers you don't have configured?"**
> "It defaults to the standard ACORD form format, which most carriers accept. But we configure it for the specific carriers in your book. The more carriers we add, the more tailored the submissions become."

**"What if we get a type of claim it hasn't seen before?"**
> "The AI handles all standard lines -- auto, home, commercial property, commercial auto, farm/ranch, workers comp, general liability. If something unusual comes in, it does its best to extract the data and flags what it's unsure about. The CSR can always fill in the gaps or escalate."

**"How much does it cost?"**
> "The AI processing cost is pennies per claim -- typically under $0.10 per FNOL processed. The real cost is the subscription, which we structure based on claim volume. But the ROI math is straightforward: if you're saving 30 minutes of CSR time per claim, at even modest hourly rates, the system pays for itself in the first week."

**"Can my CSRs actually use this?"**
> "It's a web application. If they can use email, they can use this. There's no training period beyond a 15-minute walkthrough. The demo scenarios you just saw are built into the system -- a new CSR can click through them to understand the workflow on day one."

**"What about after-hours claims?"**
> "Emails that arrive after hours get processed as soon as the system sees them. When your team arrives in the morning, the claims are already extracted, policies looked up, and ready for review. They just work through the queue."

---

## Quick Reference: Demo Scenario Summary

| Scenario | Client | Claim Type | Carrier | Key Demo Point |
|---|---|---|---|---|
| Auto Accident | Tom Rezac | Personal auto collision | Auto-Owners | Full end-to-end walkthrough |
| Hail Damage | Linda Sorensen | Homeowners property | Westfield | Property-specific handling, hail season volume |
| Farm Loss | Jim Schroeder | Farm/ranch multi-peril | Grinnell Mutual | Multi-structure complexity, livestock flagging |
| Commercial Vehicle | Great Plains Trucking | Commercial auto w/ injuries | EMC (EMCASCO) | Priority escalation, injury handling, cargo |
| Incomplete Claim | Miguel Torres | Auto comprehensive (break-in) | Auto-Owners | Missing info detection, follow-up generation |

## API Quick Reference (for technical audiences)

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/claims/intake` | POST | Submit an email for FNOL processing |
| `/api/claims` | GET | List all claims in the queue |
| `/api/claims/{id}` | GET | Get full claim details |
| `/api/claims/{id}/approve` | POST | Approve extraction, generate submission docs |
| `/api/claims/{id}/submit` | POST | Submit to carrier (marks as submitted) |
| `/api/claims/{id}/followup` | POST | Generate follow-up email for missing info |
| `/api/demo/scenarios` | GET | List available demo scenarios |
| `/api/demo/scenario/{name}` | POST | Trigger a demo scenario |
| `/api/chat` | POST | Send a chat message to the assistant |
| `/api/policies/search?q=` | GET | Search policies by number or client name |
