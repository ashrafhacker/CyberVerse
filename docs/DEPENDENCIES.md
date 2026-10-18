# Dependencies & Licenses

| Dependency | Repository | License | Purpose | Version |
|---|---|---|---|---|
| FastAPI | github.com/fastapi/fastapi | MIT | Backend API | >=0.109 |
| SQLAlchemy | github.com/sqlalchemy/sqlalchemy | MIT | ORM | >=2.0 |
| Alembic | github.com/sqlalchemy/alembic | MIT | DB migrations | >=1.13 |
| asyncpg | github.com/MagicStack/asyncpg | Apache-2.0 | Postgres driver | >=0.29 |
| Redis | github.com/redis/redis-py | MIT | Cache/broker | >=5.0 |
| Celery | github.com/celery/celery | BSD-3 | Background tasks | >=5.3 |
| Pydantic | github.com/pydantic/pydantic | MIT | Validation | >=2.5 |
| python-jose | github.com/mpdavis/python-jose | MIT | JWT | >=3.3 |
| passlib/bcrypt | github.com/pyca/bcrypt | Apache-2.0 | Password hashing | >=4.0 |
| Next.js | github.com/vercel/next.js | MIT | Web framework | 15.x |
| React | github.com/facebook/react | MIT | UI | 19 |
| Tailwind CSS | github.com/tailwindlabs/tailwindcss | MIT | Styling | 4 |
| PostgreSQL | postgresql.org | PostgreSQL License | Primary DB | 16 |
| Redis server | redis.io | BSD-3 | Cache/queue | 7 |
| Godot | github.com/godotengine/godot | MIT | Game engine | 4.x |
| Three.js | github.com/mrdoob/three.js | MIT | Browser 3D (limited) | r16x |
| CTFd (planned) | github.com/CTFd/CTFd | Apache-2.0 | CTF platform | 3.x |
| Juice Shop (optional target) | github.com/juice-shop/juice-shop | MIT | Intentionally vulnerable target | latest |

All dependencies are open source. No paid SaaS is required for local development.
Razorpay/SendGrid integrations exist in requirements but are optional and disabled by default.
