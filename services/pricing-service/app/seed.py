"""Seed default margin rules (idempotent). Run after migrations.

Establishes a global default plus per-tier margins (retail highest, government/commercial lowest),
and one per-(material,tier) example. All tunable later via the API.
"""
from __future__ import annotations

from decimal import Decimal

from .db import SessionLocal
from .models import MarginRule
from . import service


# (material_id, tier, margin_pct)
RULES = [
    (None, None, 12),            # global default
    (None, "individual", 18),    # retail buyers
    (None, "contractor", 12),
    (None, "commercial", 9),
    (None, "government", 10),
    ("cement", "individual", 20),  # example: richer margin on cement for retail
]


def seed() -> None:
    db = SessionLocal()
    try:
        for mid, tier, pct in RULES:
            # use service upsert semantics without importing heavy deps
            existing = service._find_rule(db, mid, tier)
            if existing is None:
                db.add(MarginRule(material_id=mid, tier=tier, margin_pct=Decimal(str(pct))))
        db.commit()
    finally:
        db.close()
    print("[seed] margin rules ensured")


if __name__ == "__main__":
    seed()
