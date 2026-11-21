# Google Stitch Design Handoff & Screen Inventory
**Project ID:** `12337212643351304899`  
**Project Title:** ASHA Voice Field Register  
**Platform:** Google Stitch (<https://stitch.withgoogle.com/>)  
**Design System:** Frontline Clinical Field (`assets/ea10c19f154a4c7b91de57ef3822fe74`)  
**Handoff Date:** 21 November 2026  

---

## 1. Executive Summary

The Google Stitch design phase for the **ASHA Voice Field Register** (PS1 · Healthcare) has been successfully executed using the `StitchMCP` integration. 

A unified, high-contrast, clinical-grade design system named **Frontline Clinical Field** was established to satisfy the dual requirements of:
1. **ASHA Worker Portal:** Mobile-first, voice-first, low-cognitive-load interface designed for rapid field operation between rural households under direct sunlight without normal-workflow typing.
2. **PHC Supervisor Portal:** Desktop-first, tablet-responsive operational command center for the Medical Officer In-Charge (MOIC) to monitor live danger-sign alerts, referral escalations, ASHA field workers, and offline sync integrity.

---

## 2. Generated Screens & High-Resolution Assets

### Screen 1: ASHA Worker Active Voice Session & Live Transcript
- **Screen ID:** `68b0b3c92b274caca3d1ce1c4fc9594b`
- **Resource Name:** `projects/12337212643351304899/screens/68b0b3c92b274caca3d1ce1c4fc9594b`
- **Device Type:** `MOBILE` (780 × 3158 px)
- **Title:** `Active Voice Field Visit`
- **Design System Token:** `assets/ea10c19f154a4c7b91de57ef3822fe74`
- **Artifact Links:**
  - **Screenshot:** [Download Image](https://stitch.googleapis.com/v1/projects/12337212643351304899/files/348cd63c62d949818520e22a75058f9e:download)
  - **HTML Code:** [Download HTML](https://stitch.googleapis.com/v1/projects/12337212643351304899/files/defb8c1b94e24f5f8962ca2fc980e7f9:download)
- **Core Features Implemented:**
  - Top worker banner: Worker Sunita Devi (`ASH-204`), PHC Rampur, Online/Sync status.
  - Indic Language Selector: Hindi (`hi-IN`), Kannada (`kn-IN`), Tamil (`ta-IN`), English (`en-IN`).
  - Beneficiary Context: Sunita Devi (`BEN-1042`), ANC 3rd Trimester (Week 34), High-Risk Pregnancy watch.
  - Streaming STT Waveform: Real-time dynamic visualizer with concentric glowing rings and `Barge-In Active` badge.
  - Bilingual Live Transcript: Dialogue bubbles showing ASHA questions and mother's reported dizziness and bilateral edema.
  - **Critical Danger-Sign Alert Banner:** Unmissable crimson callout (*Severe Pre-eclampsia symptoms*) with *Play Timbre Voice Referral Guidance* button.
  - Bottom Controls: Large 64x64px central microphone button with glowing state, *Stop Session*, and *Next: Review Fields*.

---

### Screen 2: ASHA Worker Structured Visit Review & Field Correction
- **Screen ID:** `e3e70ee0827d44f4a154b6a6d9e745d2`
- **Resource Name:** `projects/12337212643351304899/screens/e3e70ee0827d44f4a154b6a6d9e745d2`
- **Device Type:** `MOBILE` (780 × 2928 px)
- **Title:** `Structured Visit Review & Field Correction`
- **Artifact Links:**
  - **Screenshot:** [Download Image](https://stitch.googleapis.com/v1/projects/12337212643351304899/files/5a4ccd990c3546bfbb2890cf207624c1:download)
  - **HTML Code:** [Download HTML](https://stitch.googleapis.com/v1/projects/12337212643351304899/files/26344336807c4a68a02d54727b2db513:download)
- **Core Features Implemented:**
  - Summary Header with `Local Draft` status.
  - Extracted Vitals Grid: Blood Pressure `142/94 mmHg` (Amber Stage 1 warning), Weight `58.5 kg`, Hemoglobin `9.8 g/dL` (Mild Anemia), FHR `144 bpm`.
  - Danger-Sign Flagged: Persistent High-Risk Red callout attached to the visit record.
  - Immunisation Tracker: TT2/Booster administered today, 30 IFA tablets dispensed.
  - **Uncertain Field Voice Correction Card:** Dashed amber highlight on *Fundal Height / Gestational Age* (`[Uncertain - Confidence 62%]`) with active mic action pill: *Tap or Speak to Correct this Field*.
  - **Spoken Read-Back Confirmation:** Gnani Timbre audio player button (*Listen to Spoken Read-back in Hindi - 42s*).
  - Fixed Action Bar: Secondary *Voice Correct* button + 52px high-contrast teal *Confirm & Save Visit (BEN-1042)* button.

---

### Screen 3: PHC Supervisor Command Center & Danger Alert Queue
- **Screen ID:** `b4dd28a530a545209e6a24aaf925445c`
- **Resource Name:** `projects/12337212643351304899/screens/b4dd28a530a545209e6a24aaf925445c`
- **Device Type:** `DESKTOP` (2560 × 3284 px)
- **Title:** `PHC Command Center - Danger Alert Queue`
- **Artifact Links:**
  - **Screenshot:** [Download Image](https://stitch.googleapis.com/v1/projects/12337212643351304899/files/7a3a3ed812234e799a582ee3acc22324:download)
  - **HTML Code:** [Download HTML](https://stitch.googleapis.com/v1/projects/12337212643351304899/files/969d35b3a76d4335bcc1d3b55aaf60bf:download)
- **Core Features Implemented:**
  - Facility Header: Primary Health Centre Rampur (Mandya) with live sync indicator (`240ms` latency).
  - Multi-Dimensional Filter Toolbar: Date, Worker selector, Ward filter, Visit Type pill tags (`ANC`, `PNC`, `Immunisation`, `General`).
  - 4 Key Operational Metrics Cards:
    1. *Active Danger Alerts:* `3 Critical` (Ambulance 108 dispatch trigger).
    2. *Today's Completed Visits:* `48 / 65` (74% coverage progress).
    3. *High-Risk Pregnancies:* `14` cases.
    4. *Vaccinations Today:* `32 Doses` (100% cold-chain compliance).
  - **Left Column (60%): Live Danger-Sign Alert Queue & Referral Tracking:**
    - Item 1 (Critical Red): Sunita Devi (`BEN-1042`) with direct *Dispatch Ambulance 108* and *Call ASHA* CTAs.
    - Item 2 (High Amber): Ananya Gowda (`BEN-1088`) Severe Anemia (`Hb 6.8 g/dL`) with FRU bed confirmation.
    - Item 3 (Neonatal Watch): Baby of Meena (`BEN-1015`) Low Birth Weight (`1.9 kg`).
  - **Right Column (40%): ASHA Field Roster:**
    - Real-time roster monitoring 8 field workers with live sync badges (`Online`, `Syncing 2 Drafts`, `Offline 15m`).
    - Emergency referral pathways quick card showing transit time and bed availability.

---

### Screen 4: Beneficiary Directory & Offline Draft Sync Drawer
- **Screen ID:** `bfa5e9307bd74a22a2a4fb0dd4bdefb8`
- **Resource Name:** `projects/12337212643351304899/screens/bfa5e9307bd74a22a2a4fb0dd4bdefb8`
- **Device Type:** `TABLET` / `DESKTOP` (2560 × 2048 px)
- **Title:** `ASHA Field Tablet Portal - Beneficiary Directory & Offline Sync`
- **Artifact Links:**
  - **Screenshot:** [Download Image](https://stitch.googleapis.com/v1/projects/12337212643351304899/files/184b9d5394b34a32ba59eaf0700e9ea8:download)
  - **HTML Code:** [Download HTML](https://stitch.googleapis.com/v1/projects/12337212643351304899/files/073fb847f961483d8a41c49fc0108541:download)
- **Core Features Implemented:**
  - Top Connectivity Status Bar: *Working Offline · 3 Drafts Pending Sync* with *Sync All Now (3)* CTA.
  - Left Section (65% width): Beneficiary Field Directory with Indic voice search bar, category chips (`All`, `HRP`, `Infants Due Vaccine`, `Postnatal`), and high-contrast status strips.
  - **Right Section (35% width): IndexedDB Offline Visit Drafts Drawer:**
    - Draft 1: *Syncing (60% circular spinner, client UUID)*.
    - Draft 2: *Pending Network (Clock icon, Edit Draft)*.
    - Draft 3: *Network Timeout Error (Red badge, Retry Sync Now button)*.
    - Zero data loss guarantee sync summary.

---

### Screen 5 (Responsive Variant): PHC Command Center - Tablet Optimized
- **Screen ID:** `f61ac7d771424d32a5cb0fdce12946ca`
- **Resource Name:** `projects/12337212643351304899/screens/f61ac7d771424d32a5cb0fdce12946ca`
- **Device Type:** `TABLET` (2560 × 3486 px)
- **Title:** `PHC Command Center - Tablet Optimized`
- **Artifact Links:**
  - **Screenshot:** [Download Image](https://stitch.googleapis.com/v1/projects/12337212643351304899/files/55c682782604491da921ef17bc8a47e4:download)
  - **HTML Code:** [Download HTML](https://stitch.googleapis.com/v1/projects/12337212643351304899/files/2ad72dd7f5cf4af48ceb44d1ae4ebac3:download)
- **Core Refinements:**
  - Collapsible Filter Bar with touch-friendly chips.
  - 2x2 grid reflow for the 4 KPI summary cards.
  - Touch-calibrated triage buttons (`minimum 44px-48px` height) for tablet field touchscreens.
  - Seamless responsive stacking eliminating any horizontal scroll.

---

## 3. Design-to-Code Implementation Instructions

When translating these Stitch screens into Next.js + Tailwind CSS components:

1. **Colors in `tailwind.config.ts`:**
   ```typescript
   colors: {
     clinical: {
       primary: '#0F766E',
       'primary-dark': '#115E59',
       'primary-container': '#A3FAEF',
       secondary: '#0284C7',
       'secondary-container': '#5BB8FE',
       danger: '#DC2626',
       'danger-container': '#FFDAD6',
       warning: '#D97706',
       success: '#0D9488',
       canvas: '#F8FAFC',
       card: '#FFFFFF',
       border: '#CBD5E1',
       text: '#0F172A',
       'text-muted': '#334155',
     }
   }
   ```

2. **Touch Target Enforcement:**
   Ensure all interactive elements have `min-h-[48px]` and `min-w-[48px]`. Use `min-h-[56px]` or `min-h-[64px]` for the primary mic button and confirm-and-save buttons.

3. **Danger Alerts:**
   Always render danger-sign banners using `bg-[#FFDAD6] border-2 border-[#DC2626] text-[#0F172A]` with high-contrast alert icons and screen-reader announcements (`role="alert"`).
