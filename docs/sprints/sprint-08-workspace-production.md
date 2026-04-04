# Sprint 8 — Workspace Management & Production Features

## Goal

Add **multi-user workspace management**, **instructor analytics**, and **production-ready features** (auth, monitoring, deployment). This sprint makes the system ready for real-world use.

**Post-MVP Focus:** Transform from single-user demo to multi-user platform.

## Link to description

- **Implementation Plan:** [Phase 6: Workspace Sharing & Analytics](../description.md#phase-6-workspace-sharing--analytics)
- **Modules:** [Module 7: Course Workspace Management & Sharing](../description.md#module-7-course-workspace-management--sharing)

## Scope (in)

### 1. Authentication & Authorization (2-3 days)

**JWT-based auth:**
- User registration and login
- JWT token generation and validation
- Password hashing (bcrypt)

**Role-based access control:**
- Owner (instructor): create workspace, upload documents, view analytics
- Member (student): read-only access, chat only

**API endpoints:**
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`

### 2. Workspace Management (2-3 days)

**Workspace CRUD:**
- Create workspace with name and description
- Invite system: generate invite codes
- Join workspace via invite code
- List workspaces for user

**Data isolation:**
- Each workspace has separate document collection in Qdrant
- Filter all queries by workspace_id
- Prevent cross-workspace data leaks

**API endpoints:**
- `POST /api/v1/workspaces`
- `GET /api/v1/workspaces`
- `POST /api/v1/workspaces/{id}/invite`
- `POST /api/v1/workspaces/join/{code}`

### 3. Instructor Analytics (2-3 days)

**Student performance dashboard:**
- Topics where students struggle (high Explain mode usage)
- Average quiz scores per topic
- Most asked questions
- Session duration and engagement metrics

**Visualizations:**
- Bar chart: Socratic vs Explain mode ratio
- Line chart: Student progress over time
- Heatmap: Topic difficulty matrix

**API endpoint:**
- `GET /api/v1/workspaces/{id}/analytics`

### 4. Advanced Monitoring (2 days)

**LangFuse integration (optional):**
- Trace all LLM calls
- Track costs and latency
- Monitor prompt performance

**Basic logging:**
- Structured logging with levels (INFO, ERROR)
- Log all API requests
- Error tracking and alerting

**Health checks:**
- `GET /api/v1/health` — system status
- Check Qdrant, PostgreSQL, Redis connectivity

### 5. Production Deployment (2-3 days)

**Docker optimization:**
- Multi-stage builds for smaller images
- Production Compose profile
- Environment-based configuration

**Security hardening:**
- CORS configuration
- Rate limiting (e.g., 100 requests/hour/user)
- Input validation and sanitization
- Secrets management (never commit .env)

**Documentation:**
- Deployment guide
- Environment variables reference
- Troubleshooting guide

## Out of scope

- Kubernetes deployment (Docker Compose is sufficient)
- Advanced observability (Prometheus, Grafana)
- Payment integration
- Email notifications
- Advanced admin panel

## Readiness criteria

- [ ] Users can register, login, and access protected endpoints
- [ ] Workspaces can be created and shared via invite codes
- [ ] Data isolation works: users only see their workspace data
- [ ] Instructor analytics dashboard shows student performance
- [ ] Health check endpoint returns system status
- [ ] Production deployment guide is documented
- [ ] Security best practices are implemented (CORS, rate limiting, input validation)

## Estimated effort

**1.5-2 weeks** (10-14 days)

---

**Sprint label (GitHub):** `sprint:8`
