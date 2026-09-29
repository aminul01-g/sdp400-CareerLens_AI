# CareerLens AI — Frontend

Next.js 16 App Router client for CareerLens AI. Twenty routes, all rendering, no
mock data anywhere in the tree.

## Requirements

Node.js 20.9 or newer (Next.js 16's floor). Developed against 26.

## Setup

```bash
npm install
cp .env.example .env.local
```

Edit `.env.local`:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

> **`NEXT_PUBLIC_*` values are inlined at build time.** Setting one after a build
> has already happened requires a rebuild, not just a restart. This is the single
> most common reason a deployed frontend is still pointing at localhost.

The backend must be running and reachable. Check
`http://localhost:8000/health` reports `"database": "ok"` before starting here.

## Run

```bash
npm run dev        # http://localhost:3000
```

## Build and verify

```bash
npm run build      # production build
npx tsc --noEmit   # type check
npx eslint .       # lint
```

`npm run build` matters more than `npm run dev`: it exercises the server component
boundaries and the middleware, which a dev server tolerates and a build does not.

## Scripts

| Command | What |
|---|---|
| `npm run dev` | Development server with hot reload |
| `npm run build` | Production build |
| `npm run start` | Serve the production build |
| `npm run lint` | ESLint |

## Routes

The filesystem *is* the authorisation model. Three route groups, each with its own
layout, guard and data rules:

| Group | Access | Contents |
|---|---|---|
| `app/(public)/` | Anyone | Landing, about, features, login, register |
| `app/(app)/` | Signed in | Dashboard, profile, skills, projects, education, certifications, CV, recommendations, skill gap |
| `app/(admin)/` | Admin role | Overview, users, job roles and weights, taxonomy, evaluation |

Shared screens live at `src/components/`. The 49 shadcn/ui components in
`src/components/ui/` are preserved **byte-identically** from the original design
system — do not reformat them; they are not ours to churn.

`src/middleware.ts` guards the route tree. It can only check for the *presence* of
a token, because Edge middleware cannot call the database. The server layouts
revalidate the session against the API, so **the layout check is the security
boundary** and the middleware is a fast rejection. A client that forges the cookie
still gets a 401 from the server-side check.

## The session, and why it is in a cookie

The token is written to both `localStorage` and a cookie. The cookie exists
purely so Edge middleware can read it; without the mirror, the middleware guards
would be dead code that let an anonymous visitor into `/dashboard`, which is the
defect they exist to prevent.

## Data layer

```
src/lib/api/
  client.ts        fetch wrapper, ApiError, token handling
  types.ts         hand-mirrored Pydantic types
  <domain>.ts      one module per domain
src/lib/validation/  zod schemas for forms
src/hooks/           React Query hooks
```

**Types are mirrored by hand, not generated.** A generated client would let a
schema change reach the browser untyped and unnoticed. The cost is that the
mirrors can drift, so server 422 field errors are merged into the same zod
schemas — **the server stays the authority**, and a client that disagrees with it
is wrong.

**A mutation is a mutation, never a query.** Generating recommendations is a
`useMutation`, so simply opening `/recommendations` does not silently burn an
engine run. Getting this backwards is the most expensive client-side mistake
available here.

**Invalidation is per domain.** Creating a project invalidates the profile and the
dashboard, not the whole cache.

## Design system

Tailwind v4 with the tokens in `tailwind.config.ts`, plus the preserved shadcn/ui
component set. `content` globs already include `./app/**`, so the App Router needs
no Tailwind configuration change.

Mock data — `mockRecommendations`, `mockStats`, `mockQuizData`, the hardcoded
`12,847` / `94%` / `500+` figures, and the quiz — has all been removed.
`../scripts/verify_compliance.py` fails if any of it reappears.

## Things that will bite you

| Symptom | Cause |
|---|---|
| Every request 4xx in the browser | `NEXT_PUBLIC_API_URL` wrong, or set after the build. |
| `useSearchParams` build error | Needs a `<Suspense>` boundary. The skills search has one. |
| Middleware redirect loop | A cookie present but invalid; the server layout will 401. Check `/health`. |
| Changes not appearing | Editing a file the build does not watch. |
| A shadcn component fails to build | It needs an explicit `'use client'`; a previous build toolchain tree-shook it away. |

## Documentation

| Document | Where |
|---|---|
| Architecture and the reasoning behind it | [`../docs/architecture.md`](../docs/architecture.md) |
| API reference — generated from the live schema | [`../docs/api.md`](../docs/api.md) |
| User guide, including troubleshooting | [`../docs/user_manual.md`](../docs/user_manual.md) |
| Adding a screen | [`../docs/tutorials.md`](../docs/tutorials.md#8-add-a-frontend-screen) |
| Deployment | [`../docs/deployment.md`](../docs/deployment.md) |
| What the product cannot do | [`../docs/limitations.md`](../docs/limitations.md) |

## Deploying

Push to the repository and import into Vercel. Root directory `frontend`;
`vercel.json` supplies the build command and the security headers, so there is
nothing else to configure.

Set one environment variable, before the first build:

```
NEXT_PUBLIC_API_URL=https://<your-api-host>
```

Then set `ALLOWED_ORIGINS` on the API to the Vercel URL and redeploy the API. The
two must agree, and the order matters — an API with no allowed origins is safe, an
API allowing `*` is not. Full sequence in
[`../docs/deployment.md`](../docs/deployment.md#6-deploy-order).
