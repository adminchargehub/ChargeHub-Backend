from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.models import Booking, BookingStatus, Outlet, Plan, Station, User
from app.services.availability import _earliest_gap, find_earliest_slot

T0 = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)


def at(hours: float) -> datetime:
    return T0 + timedelta(hours=hours)


class TestEarliestGap:
    def test_free_outlet_starts_immediately(self):
        assert _earliest_gap([], T0, timedelta(hours=2)) == T0

    def test_waits_for_a_single_booking_to_end(self):
        busy = [(T0, at(3))]
        assert _earliest_gap(busy, T0, timedelta(hours=2)) == at(3)

    def test_finds_a_gap_between_two_bookings(self):
        # Busy 09:00-10:00 and 13:00-15:00 — a 3h hole at 10:00.
        busy = [(T0, at(1)), (at(4), at(6))]
        assert _earliest_gap(busy, T0, timedelta(hours=3)) == at(1)

    def test_skips_a_gap_that_is_too_small(self):
        # 1h hole at 10:00 is not enough for a 2h session; go after the second.
        busy = [(T0, at(1)), (at(2), at(5))]
        assert _earliest_gap(busy, T0, timedelta(hours=2)) == at(5)

    def test_unsorted_input_is_handled(self):
        busy = [(at(4), at(6)), (T0, at(1))]
        assert _earliest_gap(busy, T0, timedelta(hours=3)) == at(1)

    def test_bookings_already_past_are_ignored(self):
        busy = [(at(-5), at(-1))]
        assert _earliest_gap(busy, T0, timedelta(hours=2)) == T0

    def test_touching_windows_do_not_conflict(self):
        # Half-open [start, end): a booking ending at 10:00 frees 10:00 exactly.
        busy = [(T0, at(1))]
        assert _earliest_gap(busy, T0, timedelta(hours=1)) == at(1)

    def test_overlapping_bookings_collapse(self):
        busy = [(T0, at(3)), (at(1), at(5))]
        assert _earliest_gap(busy, T0, timedelta(hours=1)) == at(5)


class TestFindEarliestSlot:
    async def _station(self, db, outlet_count: int = 3) -> Station:
        station = Station(name="Test", slug="test")
        db.add(station)
        await db.flush()
        for i in range(1, outlet_count + 1):
            db.add(Outlet(station_id=station.id, index=i))
        await db.flush()
        return station

    async def _booking(self, db, station, outlet_index, start, end):
        user = User(
            email=f"u{outlet_index}-{start.hour}@t.example", full_name="U", hashed_password="x"
        )
        plan = Plan(
            name=f"P{outlet_index}-{start.hour}",
            slug=f"p{outlet_index}-{start.hour}",
            power_cap_w=100,
            energy_cap_wh=100,
            max_duration_minutes=60,
            price_kobo=1000,
        )
        db.add_all([user, plan])
        await db.flush()

        outlet = (
            await db.execute(
                select(Outlet)
                .where(Outlet.station_id == station.id)
                .where(Outlet.index == outlet_index)
            )
        ).scalar_one()
        db.add(
            Booking(
                user_id=user.id,
                outlet_id=outlet.id,
                plan_id=plan.id,
                starts_at=start,
                ends_at=end,
                status=BookingStatus.CONFIRMED,
            )
        )
        await db.flush()

    async def test_empty_station_returns_outlet_one_immediately(self, db):
        station = await self._station(db)
        slot = await find_earliest_slot(db, station.id, 120, T0)
        assert slot is not None
        assert slot.outlet_index == 1
        assert slot.starts_at == T0
        assert slot.ends_at == at(2)

    async def test_picks_a_free_outlet_over_waiting(self, db):
        station = await self._station(db)
        await self._booking(db, station, 1, T0, at(4))
        slot = await find_earliest_slot(db, station.id, 60, T0)
        assert slot is not None
        assert slot.outlet_index == 2
        assert slot.starts_at == T0

    async def test_all_busy_returns_earliest_release(self, db):
        station = await self._station(db, outlet_count=2)
        await self._booking(db, station, 1, T0, at(5))
        await self._booking(db, station, 2, T0, at(2))
        slot = await find_earliest_slot(db, station.id, 60, T0)
        assert slot is not None
        assert slot.outlet_index == 2
        assert slot.starts_at == at(2)

    async def test_station_with_no_outlets(self, db):
        station = await self._station(db, outlet_count=0)
        assert await find_earliest_slot(db, station.id, 60, T0) is None
