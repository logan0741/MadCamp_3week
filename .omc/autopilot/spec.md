# Musinsa-Price Tracker & 3D Virtual Try-On

## Full Specification Document

---

# PART 1: REQUIREMENTS ANALYSIS

## 1. Functional Requirements

### User Management
| ID | Requirement |
|----|-------------|
| FR-1.1 | User registration and authentication |
| FR-1.2 | Store user profile with height, weight, avatar status |
| FR-1.3 | Track avatar creation state (is_avatar_created boolean) |
| FR-1.4 | Persist avatar_url for 3D model access |

### Avatar Creation Pipeline
| ID | Requirement |
|----|-------------|
| FR-2.1 | Record video during onboarding for ECON processing |
| FR-2.2 | TTS-guided onboarding experience (SpeechSynthesis API) |
| FR-2.3 | Process video through ECON + SMPL-X + 3DGS pipeline |
| FR-2.4 | Store generated avatar for Unity WebGL rendering |
| FR-2.5 | Allow re-recording via "다시 모델링하기" button |

### Product Tracking
| ID | Requirement |
|----|-------------|
| FR-3.1 | Add products via Musinsa URL sharing |
| FR-3.2 | Scrape product details (title, thumbnail, price) |
| FR-3.3 | Log prices daily for historical tracking |
| FR-3.4 | Display price history with Recharts graphs |
| FR-3.5 | Show product cards in dashboard view |

### Virtual Try-On
| ID | Requirement |
|----|-------------|
| FR-4.1 | Generate garment mesh from product images (BCNet) |
| FR-4.2 | Provide 2D instant preview (IDM-VTON) |
| FR-4.3 | Render 3D avatar with garment in Unity WebGL |
| FR-4.4 | Track garment modeling status (is_garment_modeled) |

### AI Task Management
| ID | Requirement |
|----|-------------|
| FR-5.1 | Queue AI tasks via Redis |
| FR-5.2 | Process tasks with Celery workers |
| FR-5.3 | Manage VRAM allocation across models |
| FR-5.4 | Report task status to frontend |

## 2. Non-Functional Requirements

### Performance
| ID | Target |
|----|--------|
| NFR-P1 | Avatar generation < 10 minutes |
| NFR-P2 | IDM-VTON preview < 30 seconds |
| NFR-P3 | Price scraping daily at off-peak hours |
| NFR-P4 | Unity WebGL load < 5 seconds |
| NFR-P5 | API response < 200ms (non-AI) |

### UX Requirements
| ID | Requirement |
|----|-------------|
| NFR-U1 | Musinsa-style UI consistency |
| NFR-U2 | OnboardingGuard prevents access without avatar |
| NFR-U3 | TTS guides user through video recording steps |
| NFR-U4 | Progress indicators for AI task status |
| NFR-U5 | Mobile-responsive design |

### Security
| ID | Requirement |
|----|-------------|
| NFR-S1 | Secure user video upload and storage |
| NFR-S2 | Session management via Redis |
| NFR-S3 | Rate limiting on AI endpoints |
| NFR-S4 | Input validation on Musinsa URLs |

## 3. Implicit Requirements
- Video storage strategy (local/S3)
- Avatar asset storage (CDN for large files)
- Price log retention policy
- Failed task cleanup mechanism
- Notification system for async tasks
- Database migrations (Alembic)
- CORS configuration

## 4. Out of Scope
- E-commerce (no checkout/payments)
- Social features
- Recommendation engine
- Multi-retailer support
- Native mobile apps
- Multi-language support

---

# PART 2: TECHNICAL SPECIFICATION

## 1. Tech Stack

### Backend
| Technology | Version | Purpose |
|------------|---------|---------|
| FastAPI | 0.109+ | Async API framework |
| PostgreSQL | 15+ | Primary database |
| Redis | 7+ | Cache, Celery broker |
| Celery | 5.3+ | Task queue |
| SQLAlchemy | 2.0+ | Async ORM |
| Playwright | Latest | Web scraping |
| Alembic | 1.13+ | DB migrations |

### Frontend
| Technology | Version | Purpose |
|------------|---------|---------|
| Next.js | 14+ | React framework (App Router) |
| TypeScript | 5.3+ | Type safety |
| TanStack Query | 5+ | Server state |
| Zustand | 4+ | Client state |
| Recharts | 2.10+ | Price charts |
| react-unity-webgl | 9+ | 3D viewer |
| Tailwind CSS | 3.4+ | Styling |

### AI Infrastructure
| Technology | Purpose |
|------------|---------|
| ECON | Clothed human reconstruction |
| SMPL-X | Parametric body model |
| 3DGS | Real-time rendering |
| BCNet | Garment mesh extraction |
| IDM-VTON | 2D virtual try-on |
| PyTorch | AI framework |

## 2. Project Structure

```
MadCamp_3week/
├── backend/
│   ├── alembic/
│   │   └── versions/
│   ├── app/
│   │   ├── api/v1/
│   │   │   ├── auth.py
│   │   │   ├── users.py
│   │   │   ├── onboarding.py
│   │   │   ├── products.py
│   │   │   └── ai.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   └── middleware.py
│   │   ├── db/
│   │   │   ├── session.py
│   │   │   └── redis.py
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   ├── product.py
│   │   │   ├── price_log.py
│   │   │   └── ai_task.py
│   │   ├── schemas/
│   │   ├── services/
│   │   │   ├── scraper_service.py
│   │   │   └── ai_service.py
│   │   └── main.py
│   ├── workers/
│   │   ├── celery_app.py
│   │   ├── tasks/
│   │   │   ├── avatar_generation.py
│   │   │   ├── garment_modeling.py
│   │   │   ├── virtual_tryon.py
│   │   │   └── price_scraping.py
│   │   └── gpu_manager.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── (auth)/
│   │   │   │   ├── login/page.tsx
│   │   │   │   └── register/page.tsx
│   │   │   ├── (protected)/
│   │   │   │   ├── layout.tsx
│   │   │   │   ├── onboarding/page.tsx
│   │   │   │   ├── dashboard/page.tsx
│   │   │   │   ├── product/[id]/page.tsx
│   │   │   │   ├── tryon/[productId]/page.tsx
│   │   │   │   └── mypage/page.tsx
│   │   │   ├── layout.tsx
│   │   │   └── page.tsx
│   │   ├── components/
│   │   │   ├── ui/
│   │   │   ├── layout/
│   │   │   └── guards/
│   │   │       └── OnboardingGuard.tsx
│   │   ├── hooks/
│   │   │   ├── useAuth.ts
│   │   │   ├── useTTS.ts
│   │   │   └── useUnity.ts
│   │   ├── lib/
│   │   │   └── api/
│   │   └── types/
│   ├── package.json
│   └── Dockerfile
├── ai/
│   ├── pipelines/
│   │   ├── avatar_pipeline.py
│   │   ├── garment_pipeline.py
│   │   └── tryon_pipeline.py
│   └── requirements-ai.txt
├── docker/
│   └── docker-compose.yml
└── README.md
```

## 3. Database Schema

### users
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_avatar_created BOOLEAN DEFAULT FALSE,
    height DECIMAL(5,2),
    weight DECIMAL(5,2),
    avatar_url VARCHAR(500),
    avatar_mesh_url VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### products
```sql
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    musinsa_id VARCHAR(50) UNIQUE NOT NULL,
    url VARCHAR(500) NOT NULL,
    title VARCHAR(500) NOT NULL,
    thumbnail_url VARCHAR(500),
    brand VARCHAR(200),
    category VARCHAR(100),
    is_garment_modeled BOOLEAN DEFAULT FALSE,
    garment_mesh_url VARCHAR(500),
    current_price INTEGER,
    original_price INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### user_interests
```sql
CREATE TABLE user_interests (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
    notification_on BOOLEAN DEFAULT TRUE,
    target_price INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, product_id)
);
```

### price_logs
```sql
CREATE TABLE price_logs (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
    price INTEGER NOT NULL,
    discount_rate DECIMAL(5,2),
    is_sale BOOLEAN DEFAULT FALSE,
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_price_logs_product_time
ON price_logs(product_id, recorded_at DESC);
```

### ai_tasks
```sql
CREATE TABLE ai_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    task_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    input_data JSONB,
    output_data JSONB,
    error_message TEXT,
    progress INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);
```

## 4. API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/auth/register | User registration |
| POST | /api/v1/auth/login | User login |
| GET | /api/v1/user/status | Get user status |
| PATCH | /api/v1/user/profile | Update profile |
| POST | /api/v1/onboarding/upload | Upload avatar video |
| POST | /api/v1/products/track | Add product |
| GET | /api/v1/products | List products |
| GET | /api/v1/products/{id}/history | Price history |
| POST | /api/v1/ai/fit/{product_id} | Virtual try-on |
| GET | /api/v1/ai/tasks/{task_id} | Task status |
| POST | /api/v1/ai/remodel | Re-create avatar |

## 5. Key Components

### OnboardingGuard
- Checks `is_avatar_created` on protected routes
- Redirects to `/onboarding` if false
- Shows loading skeleton during check

### TTS Guide
- Uses `window.speechSynthesis` API
- Korean voice for instructions
- Steps: "정면을 보세요", "천천히 한 바퀴 돌아주세요"

### Unity WebGL Integration
- Load/display 3D avatars
- Support garment overlays
- Rotation/zoom controls

### VRAM Management
- Total: 96GB
- ECON: 40GB (priority 1)
- 3DGS: 20GB (always-on)
- BCNet: 20GB (on-demand)
- IDM-VTON: 16GB (always-on)

---

# PART 3: IMPLEMENTATION PLAN

## Phase 1: Project Setup & Infrastructure
1. Initialize monorepo structure
2. Set up Docker Compose (PostgreSQL, Redis)
3. Create FastAPI backend skeleton
4. Create Next.js frontend skeleton
5. Configure Alembic migrations

## Phase 2: Authentication & User Management
1. Implement JWT auth (register/login)
2. Create user model and schemas
3. Build auth API endpoints
4. Create frontend auth pages
5. Implement auth guards

## Phase 3: Product & Price Tracking
1. Create product/price_log models
2. Build Playwright Musinsa scraper
3. Implement product API endpoints
4. Create dashboard UI with product cards
5. Build price history charts (Recharts)

## Phase 4: Onboarding & Avatar
1. Create TTS guide component
2. Build video recording interface
3. Implement video upload API
4. Create Celery avatar generation task
5. Build MyPage with avatar viewer

## Phase 5: Virtual Try-On
1. Implement IDM-VTON 2D preview task
2. Create BCNet garment modeling task
3. Build try-on page with preview
4. Integrate Unity WebGL viewer
5. Add re-modeling functionality

## Phase 6: Polish & Integration
1. Add error handling throughout
2. Implement loading states
3. Mobile responsiveness
4. Performance optimization
5. Final testing

---

**EXPANSION_COMPLETE**
