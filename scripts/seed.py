"""Seed the pilot station and demo data.

    python -m scripts.seed

Idempotent — safe to re-run. Creates the University of Ibadan pilot station with
8 outlets (the MVP target), the four tariff plans carried over from the
prototype, and a demo customer.
"""

import asyncio

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import Outlet, Plan, Station, User, UserRole

PILOT_SLUG = "ui-pilot"
OUTLET_COUNT = 8

# Power/energy caps are real units here. The prototype's 0.06/0.08/0.20/0.32
# were dimensionless accumulator thresholds; these are watts and watt-hours and
# should be re-derived with P1 against the actual load study before the pilot.
PLANS = [
    ("Starter",  "starter",  60,   240,  240, 20000, "Lamps, small chargers"),
    ("Premium",  "premium",  80,   480,  360, 35000, "Phones, tablets"),
    ("Plus",     "plus",     200,  1200, 360, 60000, "Laptops"),
    ("Pro Plus", "pro-plus", 320,  2560, 480, 95000, "Lamp + phone + laptop"),
]


async def main() -> None:
    async with SessionLocal() as db:
        station = (
            await db.execute(select(Station).where(Station.slug == PILOT_SLUG))
        ).scalar_one_or_none()

        if station is None:
            station = Station(
                name="University of Ibadan — Pilot",
                slug=PILOT_SLUG,
                address="University of Ibadan, Ibadan, Oyo State",
                latitude=7.4433,
                longitude=3.9000,
            )
            db.add(station)
            await db.flush()
            print(f"created station {station.slug}")

        existing = {
            o.index
            for o in (
                await db.execute(select(Outlet).where(Outlet.station_id == station.id))
            )
            .scalars()
            .all()
        }
        for i in range(1, OUTLET_COUNT + 1):
            if i not in existing:
                db.add(
                    Outlet(
                        station_id=station.id,
                        index=i,
                        label=f"Socket {i}",
                        max_power_w=500,
                    )
                )
        print(f"outlets present: {OUTLET_COUNT}")

        for name, slug, power_w, energy_wh, minutes, kobo, devices in PLANS:
            found = (
                await db.execute(select(Plan).where(Plan.slug == slug))
            ).scalar_one_or_none()
            if found is None:
                db.add(
                    Plan(
                        name=name,
                        slug=slug,
                        power_cap_w=power_w,
                        energy_cap_wh=energy_wh,
                        max_duration_minutes=minutes,
                        price_kobo=kobo,
                        recommended_devices=devices,
                    )
                )
        print(f"plans present: {len(PLANS)}")

        demo_email = "demo@chargehub.ng"
        demo = (
            await db.execute(select(User).where(User.email == demo_email))
        ).scalar_one_or_none()
        if demo is None:
            db.add(
                User(
                    email=demo_email,
                    full_name="Demo Customer",
                    hashed_password=hash_password("chargehub123"),
                    role=UserRole.CUSTOMER,
                )
            )
            print(f"created demo user {demo_email} / chargehub123")

        await db.commit()
        print("seed complete")


if __name__ == "__main__":
    asyncio.run(main())
