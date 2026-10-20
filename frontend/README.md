# Marketing Intelligence and Campaign Copilot — Frontend

A complete React + TypeScript + Vite + Tailwind frontend for an AI-powered marketing
intelligence and campaign investigation SaaS product, built with a grayscale,
glassmorphic design system.

## Getting started

```bash
npm install
npm run dev      # local dev server
npm run build    # production build (outputs to dist/)
```

## What's included

- **Public landing page** (`/`) — cinematic two-panel composition with a full-screen
  looping video background, liquid-glass panels, and grayscale typography.
- **Auth flow** — Login, Sign Up, Forgot Password, and a multi-step Onboarding flow
  with simulated ingestion progress. Uses a clearly isolated development-mode mock
  auth adapter (`src/hooks/useAuth.tsx`) — any email/password combination signs you
  in. Swap this out for real auth API calls when the backend is ready.
- **Authenticated dashboard** (`/app/*`) — 17+ pages covering the full product
  surface: Overview, AI Investigations, Campaign Analytics & Comparison, Evidence
  Graph, Sources & Files, Mapping Review, Integrations, Content Studio,
  Recommendations, Experiments, Reports, Data Quality, Evaluation, Model/Ollama
  Connector, Settings, and Activity Log.

## Design system

- Two reusable glass utilities in `src/index.css`: `.liquid-glass` (light blur, for
  buttons/pills/small cards) and `.liquid-glass-strong` (heavy blur, for primary
  panels), both using a masked gradient-border technique instead of ordinary CSS
  borders.
- Strict grayscale palette (`tailwind.config.js` → `ink` scale, all HSL `0 0% X%`).
- Poppins for all UI text, Source Serif 4 italics for editorial accents.

## Project structure

```
src/
  components/
    glass/        Reusable glass UI primitives (GlassButton, GlassCard, StatusBadge…)
    layout/        Sidebar, DashboardShell, AuthShell, ProtectedRoute
  hooks/           useAuth (mock auth context)
  routes/          One file per route/page
  services/mock/   Typed mock fixtures (clearly separated from any future API client)
  types/           Shared TypeScript interfaces
```

## Connecting a real backend

- Replace `src/hooks/useAuth.tsx`'s `login`/`signup` with real API calls.
- Replace `src/services/mock/fixtures.ts` imports in each route with calls into a
  new `src/services/api/` client as the FastAPI backend becomes available — the
  typed interfaces in `src/types/` are designed to match 1:1 with backend models so
  this swap should be mechanical.
- The "Demo data" badges shown throughout the dashboard should be removed once a
  page is wired to real data.

## Notes

- This build intentionally does not fabricate real OAuth connections, real AI
  inference, or real analytics — all of that is mocked and clearly labelled per the
  product requirements (no false claims of real integrations).
- `npm run build` has been verified to type-check and build successfully.
