"""Seed the 9 reference phases and a demo spoke + consumer (idempotent). Run after migrations."""
from __future__ import annotations

from .bom import PHASES
from .db import SessionLocal
from .models import Consumer, Phase, Spoke


def seed() -> None:
    db = SessionLocal()
    try:
        for seq, name, rpf in PHASES:
            if db.get(Phase, seq) is None:
                db.add(Phase(seq=seq, name=name, repeats_per_floor=rpf))
        if db.get(Spoke, "s_medchal") is None:
            db.add(Spoke(id="s_medchal", name="Medchal Spoke", geofence="Medchal, Hyderabad North"))
            db.flush()
            db.add(Consumer(id="c_demo", name="Demo Builder", tier="individual",
                            spoke_id="s_medchal", phone="9000000000"))
        db.commit()
    finally:
        db.close()
    print("[seed] phases + demo spoke/consumer ensured")


if __name__ == "__main__":
    seed()
