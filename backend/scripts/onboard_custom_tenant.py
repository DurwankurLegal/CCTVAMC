import asyncio
from sqlalchemy import select, text
import app.core.database as db
from app.models.tenant import Tenant
from app.models.user import User
from app.core.security import hash_password
from app.services.provisioning import provision_tenant
from app.schemas.tenant import TenantCreate, TenantProvisionRequest

async def main():
    db._init_engine()
    async with db._AsyncSessionLocal() as session:
        # Check if tenant already exists
        res = await session.execute(select(Tenant).where(Tenant.slug == "durwankur"))
        tenant = res.scalar_one_or_none()
        if tenant:
            print("Tenant 'durwankur' already exists!")
            return

        # 1. Provision tenant
        payload = TenantProvisionRequest(
            tenant=TenantCreate(
                name="Durwankur Technologies Pvt. Ltd.",
                slug="durwankur",
                plan="starter",
                gstin="27AAGCD8758B1ZI",
                registered_address="Off: 18, Riddhi Siddhi Complex, Khambtalao Road, Bhandara, 441904",
                invoice_prefix="DUR"
            ),
            admin_email="dinesh@durwankur.com",
            admin_full_name="Dinesh Bharne",
            admin_password="Password@123"  # Standard temp password
        )
        print("Provisioning tenant...")
        result = await provision_tenant(session, payload, actor_user_id=None)
        await session.commit()
        print(f"Tenant provisioned successfully! Admin: {result.first_admin.email}, Password: Password@123")

        # Set RLS for current transaction to add staff
        await session.execute(
            text("SELECT set_config('app.tenant_id', :tid, false)"),
            {"tid": str(result.tenant.id)}
        )

        # 2. Add other staff members
        staff = [
            ("Pravin Gupte", "Pravin.gupte@durwankur.com", "7738651278", "manager"),
            ("Sonu", "Accounts@durwankur.com", None, "accounts"),
            ("Saurabh Bhagat", "Dev@durwanur.com", None, "technician")
        ]

        for full_name, email, phone, role in staff:
            exists = (await session.execute(
                select(User).where(User.tenant_id == result.tenant.id, User.email == email)
            )).scalar_one_or_none()
            if not exists:
                user = User(
                    tenant_id=result.tenant.id,
                    email=email,
                    full_name=full_name,
                    phone=phone,
                    hashed_password=hash_password("Password@123"),
                    role=role,
                    is_active=True,
                    must_change_password=True
                )
                session.add(user)
                print(f"Added staff: {full_name} ({email}) as {role}")
        
        await session.commit()
        print("All staff added successfully!")

if __name__ == "__main__":
    asyncio.run(main())
