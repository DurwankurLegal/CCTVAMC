import asyncio
from datetime import datetime, timezone
from sqlalchemy import select, text
import app.core.database as db
from app.models.subscription import Module, SaasPlan, PlanModule, TenantSubscription, TenantModule
from app.models.tenant import Tenant

async def seed_modules() -> None:
    db._init_engine()
    async with db._AsyncSessionLocal() as session:
        print("🌱 Seeding SaaS Modules and Plans...")

        # 1. Seed Modules
        modules_data = [
            ("sales", "Sales Management", "Outright sales, quotations, invoices, payments", False),
            ("rental", "Rental Management", "Rental products, units, recurring contracts, and deployments", False),
            ("amc", "AMC Management", "Annual Maintenance Contracts, service tickets, preventive schedules, engineer visits", False),
            ("inventory", "Inventory Management", "Parts tracking, reorder levels, stock adjustments, purchase orders", False),
            ("assets", "Asset Tracking", "Deployed assets directory tracked at customer sites", False)
        ]

        inserted_modules = {}
        for code, name, desc, is_core in modules_data:
            existing = (await session.execute(
                select(Module).where(Module.code == code)
            )).scalar_one_or_none()

            if existing is None:
                m = Module(code=code, name=name, description=desc, is_core=is_core, is_active=True)
                session.add(m)
                print(f"✔ Created Module: {name} ({code})")
                inserted_modules[code] = m
            else:
                print(f"• Module already exists: {name} ({code})")
                inserted_modules[code] = existing

        await session.flush()

        # 2. Seed SaaS Plans
        plans_data = [
            ("starter", "Starter Package", 2999.0, 5, 25, 3),
            ("growth", "Growth Package", 9999.0, 25, 200, 15),
            ("enterprise", "Enterprise Package", 29999.0, 0, 0, 0)
        ]

        inserted_plans = {}
        for code, name, price, max_users, max_sites, max_techs in plans_data:
            existing = (await session.execute(
                select(SaasPlan).where(SaasPlan.code == code)
            )).scalar_one_or_none()

            if existing is None:
                p = SaasPlan(
                    code=code, name=name, price_monthly=price,
                    max_users=max_users, max_sites=max_sites, max_technicians=max_techs,
                    is_active=True
                )
                session.add(p)
                print(f"✔ Created Plan: {name} ({code})")
                inserted_plans[code] = p
            else:
                print(f"• Plan already exists: {name} ({code})")
                inserted_plans[code] = existing

        await session.flush()

        # 3. Seed Plan Modules mappings
        # Starter gets: sales, inventory
        # Growth and Enterprise get: sales, rental, amc, inventory, assets
        plan_module_mappings = {
            "starter": ["sales", "inventory"],
            "growth": ["sales", "rental", "amc", "inventory", "assets"],
            "enterprise": ["sales", "rental", "amc", "inventory", "assets"]
        }

        for plan_code, module_codes in plan_module_mappings.items():
            plan = inserted_plans.get(plan_code)
            if not plan:
                continue
            for m_code in module_codes:
                existing = (await session.execute(
                    select(PlanModule).where(PlanModule.plan_id == plan.id, PlanModule.module_code == m_code)
                )).scalar_one_or_none()

                if existing is None:
                    pm = PlanModule(plan_id=plan.id, module_code=m_code)
                    session.add(pm)
                    print(f"✔ Assigned module '{m_code}' to plan '{plan_code}'")

        await session.flush()

        # 4. Map Existing Tenants
        tenants = (await session.execute(select(Tenant))).scalars().all()
        for tenant in tenants:
            # Check if tenant has subscription
            existing_sub = (await session.execute(
                select(TenantSubscription).where(TenantSubscription.tenant_id == tenant.id)
            )).scalar_one_or_none()

            # Default to growth plan
            plan_code = tenant.plan if tenant.plan in inserted_plans else "growth"
            plan = inserted_plans[plan_code]

            # Bypass RLS for platform operations on tenants
            conn = await session.connection()
            if conn.dialect.name == "postgresql":
                await session.execute(
                    text("SELECT set_config('app.tenant_id', :tid, false)"),
                    {"tid": str(tenant.id)}
                )

            if existing_sub is None:
                sub = TenantSubscription(
                    tenant_id=tenant.id,
                    plan_id=plan.id,
                    status="active",
                    starts_at=tenant.created_at or datetime.now(timezone.utc)
                )
                session.add(sub)
                print(f"✔ Created Subscription for tenant '{tenant.name}' with plan '{plan_code}'")
            else:
                print(f"• Subscription already exists for tenant '{tenant.name}'")

            # Enable default modules for this tenant
            default_modules = plan_module_mappings[plan_code]
            for m_code in default_modules:
                existing_tm = (await session.execute(
                    select(TenantModule).where(TenantModule.tenant_id == tenant.id, TenantModule.module_code == m_code)
                )).scalar_one_or_none()

                if existing_tm is None:
                    tm = TenantModule(
                        tenant_id=tenant.id,
                        module_code=m_code,
                        status="active",
                        starts_at=tenant.created_at or datetime.now(timezone.utc)
                    )
                    session.add(tm)
                    print(f"✔ Enabled module '{m_code}' for tenant '{tenant.name}'")

        await session.commit()
        print("🎉 Module seeding completed successfully.")

if __name__ == "__main__":
    asyncio.run(seed_modules())
