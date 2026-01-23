# Implementation Plan: Musinsa Price Tracker & 3D Virtual Try-On

## Summary

65 tasks across 5 phases, implementing a full-stack application with:
- FastAPI backend with PostgreSQL, Redis, and Celery
- Next.js 14 frontend with TypeScript
- AI pipeline infrastructure (stubs for ECON, BCNet, IDM-VTON)
- Docker-based deployment

---

## Phase 1: Project Setup & Infrastructure (9 tasks)

### T-001: Create Directory Structure
- **Description**: Create the full monorepo directory structure
- **Files**: `backend/`, `frontend/`, `ai/`, `docker/` hierarchies
- **Dependencies**: None
- **Agent**: `executor-low`

### T-002: Docker Compose Configuration
- **Description**: Create docker-compose.yml with PostgreSQL 15, Redis 7
- **Files**: `docker/docker-compose.yml`, `docker/.env.example`
- **Dependencies**: T-001
- **Agent**: `executor`

### T-003: Backend Requirements & Dockerfile
- **Description**: Create Python requirements file and Dockerfile
- **Files**: `backend/requirements.txt`, `backend/Dockerfile`
- **Dependencies**: T-001
- **Agent**: `executor-low`

### T-004: FastAPI Backend Skeleton
- **Description**: Create FastAPI app with CORS, middleware setup
- **Files**: `backend/app/main.py`, `backend/app/__init__.py`, `backend/app/core/config.py`
- **Dependencies**: T-001, T-003
- **Agent**: `executor`

### T-005: Database Session Configuration
- **Description**: Set up async SQLAlchemy session factory
- **Files**: `backend/app/db/session.py`, `backend/app/db/base.py`
- **Dependencies**: T-004
- **Agent**: `executor`

### T-006: Redis Connection Setup
- **Description**: Set up Redis connection pool for cache and Celery broker
- **Files**: `backend/app/db/redis.py`
- **Dependencies**: T-004
- **Agent**: `executor`

### T-007: Alembic Migration Setup
- **Description**: Initialize Alembic for database migrations
- **Files**: `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/script.py.mako`
- **Dependencies**: T-005
- **Agent**: `executor`

### T-008: Frontend Skeleton (Next.js 14)
- **Description**: Initialize Next.js 14 with App Router, TypeScript, Tailwind
- **Files**: `frontend/package.json`, `frontend/tsconfig.json`, `frontend/tailwind.config.ts`, `frontend/next.config.js`, `frontend/src/app/layout.tsx`, `frontend/src/app/page.tsx`, `frontend/src/app/globals.css`
- **Dependencies**: T-001
- **Agent**: `executor`

### T-009: Frontend Dockerfile
- **Description**: Create Dockerfile for Next.js frontend
- **Files**: `frontend/Dockerfile`, `frontend/.dockerignore`
- **Dependencies**: T-008
- **Agent**: `executor-low`

---

## Phase 2: Authentication & User Management (16 tasks)

### T-010: User Model
- **Description**: Create SQLAlchemy User model with is_avatar_created, height, weight, avatar_url
- **Files**: `backend/app/models/user.py`, `backend/app/models/__init__.py`
- **Dependencies**: T-005
- **Agent**: `executor`

### T-011: User Schemas (Pydantic)
- **Description**: Create Pydantic schemas for User operations
- **Files**: `backend/app/schemas/user.py`, `backend/app/schemas/__init__.py`
- **Dependencies**: T-010
- **Agent**: `executor`

### T-012: Security Module (JWT)
- **Description**: Implement JWT token creation, verification, password hashing
- **Files**: `backend/app/core/security.py`
- **Dependencies**: T-004
- **Agent**: `executor`

### T-013: Auth Middleware & Dependencies
- **Description**: Create JWT auth middleware and route dependencies
- **Files**: `backend/app/core/middleware.py`, `backend/app/api/deps.py`
- **Dependencies**: T-012
- **Agent**: `executor`

### T-014: Auth API Endpoints
- **Description**: Implement /auth/register and /auth/login endpoints
- **Files**: `backend/app/api/v1/auth.py`, `backend/app/api/v1/__init__.py`
- **Dependencies**: T-010, T-011, T-012, T-013
- **Agent**: `executor`

### T-015: User API Endpoints
- **Description**: Implement /user/status and /user/profile endpoints
- **Files**: `backend/app/api/v1/users.py`
- **Dependencies**: T-014
- **Agent**: `executor`

### T-016: User Migration
- **Description**: Create Alembic migration for users table
- **Files**: `backend/alembic/versions/001_create_users_table.py`
- **Dependencies**: T-007, T-010
- **Agent**: `executor`

### T-017: Frontend API Client Setup
- **Description**: Set up Axios client with auth interceptors
- **Files**: `frontend/src/lib/api/client.ts`, `frontend/src/lib/api/index.ts`
- **Dependencies**: T-008
- **Agent**: `executor`

### T-018: Frontend Types
- **Description**: Create TypeScript types for User and API responses
- **Files**: `frontend/src/types/index.ts`, `frontend/src/types/user.ts`, `frontend/src/types/api.ts`
- **Dependencies**: T-008
- **Agent**: `executor`

### T-019: Auth Store (Zustand)
- **Description**: Create Zustand store for auth state management
- **Files**: `frontend/src/stores/auth.ts`, `frontend/src/stores/index.ts`
- **Dependencies**: T-008
- **Agent**: `executor`

### T-020: useAuth Hook
- **Description**: Create useAuth hook with login, logout, register functions
- **Files**: `frontend/src/hooks/useAuth.ts`
- **Dependencies**: T-017, T-019
- **Agent**: `executor`

### T-021: UI Component Library
- **Description**: Create base UI components (Button, Card, Input, Skeleton)
- **Files**: `frontend/src/components/ui/Button.tsx`, `frontend/src/components/ui/Card.tsx`, `frontend/src/components/ui/Input.tsx`, `frontend/src/components/ui/Skeleton.tsx`, `frontend/src/components/ui/index.ts`
- **Dependencies**: T-008
- **Agent**: `designer`

### T-022: Login Page
- **Description**: Create login page with form, validation, error handling
- **Files**: `frontend/src/app/(auth)/login/page.tsx`, `frontend/src/app/(auth)/layout.tsx`
- **Dependencies**: T-020, T-021
- **Agent**: `designer`

### T-023: Register Page
- **Description**: Create registration page with height/weight fields
- **Files**: `frontend/src/app/(auth)/register/page.tsx`
- **Dependencies**: T-020, T-021
- **Agent**: `designer`

### T-024: AuthGuard Component
- **Description**: Create guard that redirects unauthenticated users to login
- **Files**: `frontend/src/components/guards/AuthGuard.tsx`
- **Dependencies**: T-020
- **Agent**: `executor`

### T-025: Protected Layout Shell
- **Description**: Create protected layout with AuthGuard wrapper
- **Files**: `frontend/src/app/(protected)/layout.tsx`
- **Dependencies**: T-024
- **Agent**: `executor`

---

## Phase 3: Product & Price Tracking (16 tasks)

### T-026: Product Model
- **Description**: Create SQLAlchemy Product model with musinsa_id, is_garment_modeled
- **Files**: `backend/app/models/product.py`
- **Dependencies**: T-005
- **Agent**: `executor`

### T-027: PriceLog Model
- **Description**: Create SQLAlchemy PriceLog model with time-series index
- **Files**: `backend/app/models/price_log.py`
- **Dependencies**: T-026
- **Agent**: `executor`

### T-028: UserInterest Model
- **Description**: Create SQLAlchemy UserInterest join model (user_id, product_id)
- **Files**: `backend/app/models/user_interest.py`
- **Dependencies**: T-010, T-026
- **Agent**: `executor`

### T-029: Product Schemas
- **Description**: Create Pydantic schemas for Product operations
- **Files**: `backend/app/schemas/product.py`
- **Dependencies**: T-026
- **Agent**: `executor`

### T-030: Products Migration
- **Description**: Create Alembic migration for products, price_logs, user_interests
- **Files**: `backend/alembic/versions/002_create_products_tables.py`
- **Dependencies**: T-016, T-026, T-027, T-028
- **Agent**: `executor`

### T-031: Musinsa URL Parser Utility
- **Description**: Create utility to extract musinsa_id from URLs with validation
- **Files**: `backend/app/utils/musinsa_parser.py`, `backend/app/utils/__init__.py`
- **Dependencies**: T-004
- **Agent**: `executor`

### T-032: Musinsa Scraper Service
- **Description**: Create Playwright-based scraper for product details and prices
- **Files**: `backend/app/services/scraper_service.py`, `backend/app/services/__init__.py`
- **Dependencies**: T-031
- **Agent**: `executor`

### T-033: Product API Endpoints
- **Description**: Implement /products endpoints (track, list, detail, history, untrack)
- **Files**: `backend/app/api/v1/products.py`
- **Dependencies**: T-029, T-032, T-013
- **Agent**: `executor`

### T-034: Frontend Product Types
- **Description**: Create TypeScript types for Product and PriceLog
- **Files**: `frontend/src/types/product.ts`
- **Dependencies**: T-018
- **Agent**: `executor`

### T-035: Product API Hooks
- **Description**: Create TanStack Query hooks for product operations
- **Files**: `frontend/src/hooks/useProducts.ts`, `frontend/src/hooks/usePriceHistory.ts`
- **Dependencies**: T-017, T-034
- **Agent**: `executor`

### T-036: ProductCard Component
- **Description**: Create product card with thumbnail, title, price, discount badge
- **Files**: `frontend/src/components/product/ProductCard.tsx`
- **Dependencies**: T-021, T-034
- **Agent**: `designer`

### T-037: AddProductModal Component
- **Description**: Create modal for adding product via Musinsa URL
- **Files**: `frontend/src/components/product/AddProductModal.tsx`
- **Dependencies**: T-021, T-035
- **Agent**: `designer`

### T-038: PriceChart Component
- **Description**: Create Recharts-based price history line chart
- **Files**: `frontend/src/components/product/PriceChart.tsx`
- **Dependencies**: T-008
- **Agent**: `designer`

### T-039: Dashboard Page
- **Description**: Create dashboard with product grid and add button
- **Files**: `frontend/src/app/(protected)/dashboard/page.tsx`
- **Dependencies**: T-025, T-035, T-036, T-037
- **Agent**: `designer`

### T-040: Product Detail Page
- **Description**: Create product detail page with price chart and try-on button
- **Files**: `frontend/src/app/(protected)/product/[id]/page.tsx`
- **Dependencies**: T-035, T-038
- **Agent**: `designer`

### T-041: Header Component
- **Description**: Create header with navigation links (dashboard, mypage, logout)
- **Files**: `frontend/src/components/layout/Header.tsx`, `frontend/src/components/layout/index.ts`
- **Dependencies**: T-021, T-020
- **Agent**: `designer`

---

## Phase 4: Onboarding & Avatar (16 tasks)

### T-042: AI Task Model
- **Description**: Create SQLAlchemy AITask model with status, progress, input/output_data
- **Files**: `backend/app/models/ai_task.py`
- **Dependencies**: T-010
- **Agent**: `executor`

### T-043: AI Task Schemas
- **Description**: Create Pydantic schemas for AITask operations
- **Files**: `backend/app/schemas/ai_task.py`
- **Dependencies**: T-042
- **Agent**: `executor`

### T-044: AI Tasks Migration
- **Description**: Create Alembic migration for ai_tasks table
- **Files**: `backend/alembic/versions/003_create_ai_tasks_table.py`
- **Dependencies**: T-030, T-042
- **Agent**: `executor`

### T-045: Celery Configuration
- **Description**: Set up Celery app with Redis broker and task routes
- **Files**: `backend/workers/__init__.py`, `backend/workers/celery_app.py`
- **Dependencies**: T-006
- **Agent**: `executor`

### T-046: GPU Manager
- **Description**: Create VRAM allocation manager for concurrent AI tasks
- **Files**: `backend/workers/gpu_manager.py`
- **Dependencies**: T-045
- **Agent**: `executor`

### T-047: Avatar Generation Task (Stub)
- **Description**: Create Celery task structure for ECON avatar generation
- **Files**: `backend/workers/tasks/__init__.py`, `backend/workers/tasks/avatar_generation.py`
- **Dependencies**: T-045, T-046
- **Agent**: `executor`

### T-048: Video Upload Endpoint
- **Description**: Implement /onboarding/upload endpoint for video upload with file validation
- **Files**: `backend/app/api/v1/onboarding.py`
- **Dependencies**: T-013, T-042, T-047
- **Agent**: `executor`

### T-049: AI Status Endpoint
- **Description**: Implement /ai/tasks/{task_id} status endpoint
- **Files**: `backend/app/api/v1/ai.py`
- **Dependencies**: T-043, T-013
- **Agent**: `executor`

### T-050: Remodel Endpoint
- **Description**: Implement /ai/remodel endpoint for avatar re-creation
- **Files**: (modify) `backend/app/api/v1/ai.py`
- **Dependencies**: T-049
- **Agent**: `executor`

### T-051: useTTS Hook
- **Description**: Create hook using SpeechSynthesis API for Korean TTS
- **Files**: `frontend/src/hooks/useTTS.ts`
- **Dependencies**: T-008
- **Agent**: `executor`

### T-052: VideoRecorder Component
- **Description**: Create video recording component using MediaRecorder API
- **Files**: `frontend/src/components/onboarding/VideoRecorder.tsx`
- **Dependencies**: T-008
- **Agent**: `executor`

### T-053: OnboardingGuide Component
- **Description**: Create TTS-guided onboarding UI with step indicators
- **Files**: `frontend/src/components/onboarding/OnboardingGuide.tsx`
- **Dependencies**: T-051, T-021
- **Agent**: `designer`

### T-054: Onboarding Page
- **Description**: Create full onboarding page combining guide and recorder
- **Files**: `frontend/src/app/(protected)/onboarding/page.tsx`
- **Dependencies**: T-052, T-053
- **Agent**: `designer`

### T-055: OnboardingGuard Component
- **Description**: Create guard that checks is_avatar_created and redirects to onboarding
- **Files**: `frontend/src/components/guards/OnboardingGuard.tsx`
- **Dependencies**: T-020
- **Agent**: `executor`

### T-056: MyPage with Avatar Info
- **Description**: Create MyPage with profile info, avatar status, re-model button
- **Files**: `frontend/src/app/(protected)/mypage/page.tsx`
- **Dependencies**: T-025, T-020, T-021
- **Agent**: `designer`

### T-057: AI Task Status Hook
- **Description**: Create hook for polling AI task status with progress
- **Files**: `frontend/src/hooks/useAITask.ts`
- **Dependencies**: T-017, T-018
- **Agent**: `executor`

---

## Phase 5: Integration & Final Wiring (8 tasks)

### T-058: Virtual Try-On Task (Stub)
- **Description**: Create Celery task structure for IDM-VTON 2D preview
- **Files**: `backend/workers/tasks/virtual_tryon.py`
- **Dependencies**: T-045, T-046
- **Agent**: `executor`

### T-059: Garment Modeling Task (Stub)
- **Description**: Create Celery task structure for BCNet garment mesh
- **Files**: `backend/workers/tasks/garment_modeling.py`
- **Dependencies**: T-045, T-046
- **Agent**: `executor`

### T-060: Try-On API Endpoint
- **Description**: Implement /ai/fit/{product_id} endpoint
- **Files**: (modify) `backend/app/api/v1/ai.py`
- **Dependencies**: T-049, T-058
- **Agent**: `executor`

### T-061: Price Scraping Celery Task
- **Description**: Create scheduled task for daily price scraping
- **Files**: `backend/workers/tasks/price_scraping.py`
- **Dependencies**: T-045, T-032
- **Agent**: `executor`

### T-062: Update Protected Layout with OnboardingGuard
- **Description**: Add OnboardingGuard to protected routes (except /onboarding itself)
- **Files**: (modify) `frontend/src/app/(protected)/layout.tsx`
- **Dependencies**: T-055
- **Agent**: `executor`

### T-063: Try-On Page
- **Description**: Create try-on page with 2D preview and status indicator
- **Files**: `frontend/src/app/(protected)/tryon/[productId]/page.tsx`
- **Dependencies**: T-035, T-057
- **Agent**: `designer`

### T-064: API Router Registration
- **Description**: Wire all API routers into main.py
- **Files**: (modify) `backend/app/main.py`
- **Dependencies**: T-014, T-015, T-033, T-048, T-049, T-060
- **Agent**: `executor`

### T-065: Error Boundary & Loading States
- **Description**: Add error boundary and consistent loading states
- **Files**: `frontend/src/components/ErrorBoundary.tsx`
- **Dependencies**: T-021
- **Agent**: `executor`

---

## Task Dependency Summary

### Phase 1 (Setup): T-001 → T-009
- T-001 is base
- T-004, T-008 can run in parallel after T-001
- T-005, T-006 depend on T-004
- T-007 depends on T-005

### Phase 2 (Auth): T-010 → T-025
- T-010 depends on T-005
- T-012 can run parallel with T-010
- T-014 waits for T-010, T-011, T-012, T-013
- Frontend tasks (T-017-T-025) can start after T-008

### Phase 3 (Products): T-026 → T-041
- T-026 depends on T-005
- T-027 depends on T-026
- T-028 depends on T-010 AND T-026
- T-030 depends on T-016, T-026, T-027, T-028
- Frontend tasks parallel after dependencies met

### Phase 4 (Onboarding): T-042 → T-057
- T-042 depends on T-010
- T-045 depends on T-006
- T-047, T-048 depend on T-045
- T-055 (OnboardingGuard) is CRITICAL - must complete before T-062

### Phase 5 (Integration): T-058 → T-065
- T-062 (layout update) depends on T-055
- T-064 (router registration) is final backend task
- T-065 can run anytime after T-021

---

## Parallel Execution Opportunities

**Group A (After T-001)**: T-002, T-003, T-004, T-008

**Group B (After T-004)**: T-005, T-006, T-012, T-031

**Group C (After T-008)**: T-017, T-018, T-019, T-021, T-051, T-052

**Group D (After T-005)**: T-010, T-026

**Group E (Backend Models)**: T-027 (after T-026), T-042 (after T-010)

**Group F (Frontend Pages)**: T-039, T-040, T-054, T-056, T-063 (after their component deps)

---

## Agent Distribution

| Agent | Count | Tasks |
|-------|-------|-------|
| executor-low | 3 | T-001, T-003, T-009 |
| executor | 48 | All infrastructure, models, APIs, hooks, guards |
| designer | 14 | T-021-T-023, T-036-T-041, T-053-T-054, T-056, T-063 |

---

## Critical Path

```
T-001 → T-004 → T-005 → T-010 → T-014 → T-015 → T-033 → T-064
                  ↓
               T-006 → T-045 → T-047 → T-048
                                         ↓
                              (Backend Complete)

T-001 → T-008 → T-017 → T-020 → T-024 → T-025 → T-055 → T-062
                                                          ↓
                                               (Frontend Complete)
```

---

**PLANNING_COMPLETE**
