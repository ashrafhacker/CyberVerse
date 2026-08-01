# CyberVerse

An immersive 3D cybersecurity academy where users learn cybersecurity through fictional, isolated simulations, guided by AI, with story-driven missions, labs, and role-playing.

## 🎯 Mission

CyberVerse is a production-ready educational cybersecurity simulation platform that teaches cybersecurity through safe, fictional environments designed for learning and defense.

## 🏗️ Architecture

```
CyberVerse/
├── frontend/          # Next.js 15+ React application
├── backend/           # FastAPI Python backend
├── database/          # PostgreSQL schema & migrations
├── game/              # Unreal Engine 5 game client
├── auth/              # Authentication service
├── admin/             # Admin portal
├── ai/                # AI mentor & services
├── docs/              # Documentation
├── tests/             # Test suites
├── scripts/           # Utility scripts
├── devops/            # CI/CD & deployment configs
└── docker/            # Docker configurations
```

## 🛠️ Technology Stack

### Frontend
- Next.js 15+ (App Router)
- React 19
- TypeScript
- Tailwind CSS
- Framer Motion
- PWA Support

### Backend
- FastAPI
- Python 3.12+
- SQLAlchemy 2.0 (Async)
- Alembic (Migrations)
- Redis (Caching/Sessions)
- Celery (Background Jobs)

### Database
- PostgreSQL 16 (Supabase)

### Authentication
- JWT + Refresh Tokens
- OAuth (Google, GitHub)
- 2FA (TOTP)
- Device Session Management

### Infrastructure
- Frontend: Vercel
- Backend: Render
- Database: Supabase PostgreSQL
- Auth: Supabase Auth
- Storage: Supabase Storage
- Containerization: Docker
- CI/CD: GitHub Actions

## 🚀 Quick Start

### Prerequisites
- Node.js 20+
- Python 3.12+
- PostgreSQL 16+
- Docker & Docker Compose

### Development Setup

```bash
# Clone repository
git clone https://github.com/yourorg/cyberverse.git
cd CyberVerse

# Start development environment
docker-compose -f docker/docker-compose.dev.yml up -d

# Install frontend dependencies
cd frontend && npm install

# Install backend dependencies
cd ../backend && pip install -e .

# Run database migrations
cd ../backend && alembic upgrade head

# Start development servers
# Terminal 1: Frontend
cd frontend && npm run dev

# Terminal 2: Backend
cd backend && uvicorn app.main:app --reload
```

## 📦 Project Structure

### Frontend (`/frontend`)
```
frontend/
├── src/
│   ├── app/                    # Next.js App Router pages
│   │   ├── (auth)/            # Auth layout group
│   │   ├── (dashboard)/       # Dashboard layout group
│   │   ├── (admin)/           # Admin layout group
│   │   ├── (instructor)/      # Instructor layout group
│   │   └── api/               # API routes
│   ├── components/            # React components
│   │   ├── ui/               # Base UI components
│   │   ├── forms/            # Form components
│   │   ├── charts/           # Chart components
│   │   └── layout/           # Layout components
│   ├── lib/                   # Utilities & configurations
│   ├── hooks/                 # Custom React hooks
│   ├── store/                 # State management (Zustand)
│   ├── types/                 # TypeScript types
│   └── styles/                # Global styles
├── public/                    # Static assets
└── tests/                     # Frontend tests
```

### Backend (`/backend`)
```
backend/
├── app/
│   ├── api/                   # API routes
│   │   ├── v1/               # API v1 endpoints
│   │   └── deps.py           # FastAPI dependencies
│   ├── core/                  # Core configurations
│   │   ├── config.py         # Settings management
│   │   ├── security.py       # Security utilities
│   │   └── database.py       # Database connection
│   ├── models/                # SQLAlchemy models
│   ├── schemas/               # Pydantic schemas
│   ├── services/              # Business logic
│   ├── repositories/          # Data access layer
│   ├── tasks/                 # Celery tasks
│   └── main.py               # FastAPI application
├── alembic/                   # Database migrations
├── tests/                     # Backend tests
└── pyproject.toml            # Python project config
```

## 🔐 User Roles & Permissions

| Role | Description | Permissions |
|------|-------------|-------------|
| Guest | Unauthenticated user | View public content |
| Student | Registered learner | Access courses, missions, labs |
| Premium Student | Paid subscriber | All student + premium content |
| Instructor | Course creator | Create/manage content, view student progress |
| Moderator | Community moderator | Moderate discussions, flag content |
| Administrator | Platform admin | Full platform management |
| Developer | Technical staff | Access dev tools, logs |
| Super Admin | Platform owner | All permissions + system config |

## 🎮 Game Features

- **Story Mode**: Campaign from beginner to expert
- **Free Roam**: Explore Cyber Academy facilities
- **Practice Labs**: Unlimited hands-on simulations
- **Challenge Mode**: Timed scenarios
- **Daily/Weekly Missions**: Rotating objectives
- **Multiplayer**: Co-op learning, instructor-led sessions

## 🤖 AI System

- AI Mentor: Personalized guidance & explanations
- AI Tutor: Interactive learning assistance
- Quiz Generator: Dynamic assessments
- Progress Analyzer: Learning insights
- Mission Hint System: Contextual help

## 🌐 Neo Analysis Simulation System

The realistic simulation layer: a complete **virtual internet** of fictional companies, infrastructure, and threat actors that react to player actions in real time.

- **Virtual Internet**: banks, hospitals, data centers, airports, smart cities, and more — each with employees, email, DNS, Active Directory, logs, alerts, and backups (all fictional)
- **Dynamic AI World**: procedurally generated companies, users, devices, incidents, and threat timelines — every playthrough is different
- **Real Defensive Work**: investigate alerts, review logs, analyze malware in sandboxes, configure firewalls, patch systems, perform forensics, respond to incidents
- **AI Mentor**: explains tasks, teaches concepts, reviews decisions, adapts missions to your skill
- **Safe Training Labs**: connect your own VMs, Docker labs, or home labs with **mandatory ownership verification** and strict scope enforcement
- **Safety First**: no arbitrary third-party targets, no real credentials, sandboxed analysis, full audit trail

See [docs/neo-analysis.md](docs/neo-analysis.md) for the full design.

## 📚 Learning Paths

1. Cybersecurity Fundamentals
2. Networking
3. Linux Administration
4. Windows Administration
5. Programming Fundamentals (Python, JavaScript)
6. Web Security
7. Cloud Security
8. Digital Forensics
9. Incident Response
10. Threat Hunting
11. Security Operations
12. Governance & Compliance

## 🔒 Security Features

- Zero Trust Architecture
- End-to-end Encryption
- Rate Limiting & DDoS Protection
- Audit Logging
- Automated Security Scanning
- Regular Penetration Testing
- GDPR/Privacy Compliance

## 🧪 Testing

```bash
# Frontend tests
cd frontend && npm run test        # Unit tests
cd frontend && npm run test:e2e    # E2E tests (Playwright)

# Backend tests
cd backend && pytest               # Unit & integration tests
cd backend && pytest --cov         # With coverage
```

## 📖 Documentation

- [Architecture Guide](docs/architecture.md)
- [API Documentation](docs/api.md)
- [Database Schema](docs/database.md)
- [Deployment Guide](docs/deployment.md)
- [Security Guide](docs/security.md)
- [Developer Handbook](docs/developer-guide.md)

## 🚢 Deployment

### Environments
- **Development**: Local Docker Compose
- **Staging**: Render + Vercel Preview
- **Production**: Render + Vercel + Supabase

### CI/CD Pipeline
1. Lint & Type Check
2. Unit Tests
3. Integration Tests
4. Build Docker Images
5. Deploy to Staging
6. Smoke Tests
7. Deploy to Production (manual approval)

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Unreal Engine 5 for 3D rendering
- FastAPI for the backend framework
- Next.js for the frontend framework
- Supabase for backend services
- All open-source contributors

---

**CyberVerse** - Learn Cybersecurity Through Immersive Simulation