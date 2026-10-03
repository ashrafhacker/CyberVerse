import asyncio
from sqlalchemy import text
from app.core.database import engine

async def seed():
    async with engine.begin() as conn:
        await conn.execute(text('DELETE FROM subscription_plans;'))
        
        await conn.execute(text("""
            INSERT INTO subscription_plans (id, slug, name, description, tier, price_amount, price_currency, billing_interval, billing_interval_count, trial_days, is_active, display_order, created_at, updated_at) 
            VALUES 
            (gen_random_uuid(), 'beginner-plan', 'Beginner', 'Basic access to beginner modules', 'MONTHLY', 99.00, 'INR', 'month', 1, 0, true, 1, now(), now()),
            (gen_random_uuid(), 'intermediate-plan', 'Intermediate', 'Access to intermediate modules', 'QUARTERLY', 399.00, 'INR', 'month', 1, 0, true, 2, now(), now()),
            (gen_random_uuid(), 'advanced-softwares-plan', 'Advanced with Softwares', 'Full access including advanced modules and required softwares', 'ANNUAL', 5000.00, 'INR', 'month', 1, 0, true, 3, now(), now())
        """))
    print('Plans seeded!')

asyncio.run(seed())
