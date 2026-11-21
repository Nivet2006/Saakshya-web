# Google Stitch Design Brief — ASHA Voice Field Register

Use this brief directly in Google Stitch (https://stitch.withgoogle.com/) as the initial project prompt. Create the project as **ASHA Voice Field Register**.

## Master Stitch prompt

Design a polished, high-fidelity, responsive healthcare field-work platform called **ASHA Voice Field Register**. It has two connected experiences sharing one design system:

1. **ASHA Worker Portal:** mobile-first and voice-first. An ASHA worker must be able to use the application while moving between household visits, with minimal cognitive load and no normal-workflow typing. The dominant action is starting a voice visit. Make language, microphone, connection, transcription, assistant speaking, interruption and save/confirmation states unmistakable. Use large touch targets, clear typography, high contrast, calm visual hierarchy and carefully designed alert states.
2. **PHC Supervisor Portal:** a professional operational command center for desktop, still responsive on tablet and mobile. It lets authorized supervisors monitor danger alerts, ASHA workers, visits, referrals, follow-ups, immunisation status and coverage reports.

Create one coherent design language for both experiences. The visual direction should feel trustworthy, modern, calm, practical and appropriate for public healthcare—not a generic SaaS admin template and not a flashy consumer wellness app. Use restrained colours with semantic status colours, accessible contrast, clear hierarchy, consistent spacing, reusable cards/tables/forms/navigation and realistic synthetic sample content. Use no real patient data.

### ASHA worker screens to create

- Sign in and language selection.
- Worker home: today's assigned visits, assigned beneficiaries and upcoming follow-ups.
- Beneficiary search/list and beneficiary profile.
- Start visit and identify/confirm beneficiary.
- Active voice session: prominent microphone control, waveform/audio level, selected language, live transcript, connection state and concise guidance.
- Clear visual states for listening, partial transcription, processing, assistant speaking, interruption, reconnecting, microphone permission denied and disconnected.
- Structured visit draft with beneficiary ID, visit type, weight, vaccinations due, next visit date and danger-sign state.
- Read-back review with explicit confirm action.
- Voice correction state that highlights the field being corrected.
- High-priority danger-sign alert that cannot be visually confused with ordinary notifications and presents the referral instruction prominently.
- Visit history/detail, immunisation tracking and follow-up queue/detail.
- Offline draft list with pending, syncing, synced, failed and conflict states.

### Supervisor screens to create

- PHC command center with operational summary and recent activity.
- Live danger-sign alert queue with severity/status, PHC scope and timestamp; alert detail with acknowledgement/referral tracking.
- ASHA worker list and worker details.
- Beneficiary administration/list/detail.
- Visit register with clear filters and visit details.
- Follow-up and immunisation monitoring.
- Referral tracking.
- Analytics and coverage reports with date/filter scope clearly visible.
- Export and audit trail views.

### Responsive requirements

Create explicit design variants/frames for:
- Small mobile, around 360–390 px wide.
- Large mobile, around 414–430 px wide.
- Tablet, around 768–1024 px wide.
- Desktop, around 1280–1440 px wide.

Do not simply shrink desktop screens. Make the worker voice action prominent and reachable on mobile. Use adaptive navigation. Turn dense supervisor tables into readable cards or lists on narrow screens. Ensure dialogs, forms, charts, alert banners, filters and navigation reflow cleanly. Avoid clipped text and horizontal page overflow. Keep interactive targets approximately 44 × 44 CSS px or larger wherever practical. Critical alerts and the main voice action must remain visible at all sizes.

### Prototype these flows

1. Worker: sign in → select language → choose beneficiary → start voice session → view live transcript → review structured visit → hear/read-back → correct a field by voice → confirm → saved visit → follow-up.
2. Danger sign: active voice session → urgent danger alert → referral instruction → alert remains attached to visit → supervisor can see the alert.
3. Supervisor: command center → open danger alert → inspect permitted details → acknowledge/update referral status → audit trail.

Represent realistic states and transitions, but do not imply that this prototype is connected to a live backend.

### Design system output

Create/export an agent-friendly `DESIGN.md` covering colour and semantic tokens, typography, spacing, grid, breakpoints, navigation, controls, cards, tables, dialogs, alert patterns, voice-session states, accessibility and responsive behaviour. Use reusable components and consistent states (default, hover, focus, active, disabled, loading and error).

The result must be implementation-ready: clear enough for a Next.js + TypeScript team to reproduce with reusable components. Avoid placeholder lorem ipsum, generic charts with fabricated claims, tiny controls, overdecorated gradients, excessive glassmorphism and meaningless decorative buttons.

## Design review checklist

- Does the worker understand how to start a visit immediately?
- Is the voice interaction clearly the primary action on mobile?
- Are listening, processing, speaking, interrupted and disconnected states visually distinct?
- Is a danger alert unmistakable and accessible?
- Can a worker review, correct and confirm a structured record without typing?
- Can a supervisor identify and track unresolved alerts and referrals?
- Do all important screens have mobile, tablet and desktop variants?
- Are tables, dialogs, charts and navigation usable at narrow widths?
- Is the same design system used by both portals?
- Can every designed component be mapped to a real application route/state?

## Required handoff from Stitch to repository

Save the actual Stitch project/share reference if available, export `DESIGN.md` to `docs/DESIGN.md`, and create `docs/STITCH_DESIGN_HANDOFF.md` describing chosen screens, flows, breakpoints, component mapping and implementation notes. Do not fabricate the project URL or claim an export exists if it was not created.
