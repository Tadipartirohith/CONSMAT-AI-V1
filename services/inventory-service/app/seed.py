"""Seed the materials reference data (idempotent). Run after migrations.

Usage: python -m app.seed
"""
from __future__ import annotations

from decimal import Decimal

from .db import SessionLocal
from .models import Material

# Base catalog carried from V0 (per_sqft = BOM coefficient).
MATERIALS = [
    {"id": "cement", "name": "Cement", "category": "binder", "unit": "bags",
     "grade": "OPC 53-Grade", "per_sqft": Decimal("0.40")},
    {"id": "steel", "name": "TMT Steel", "category": "reinforcement", "unit": "tonnes",
     "grade": "Fe 500D", "per_sqft": Decimal("0.004")},
    {"id": "sand", "name": "River Sand", "category": "aggregate", "unit": "tonnes",
     "grade": "Fine (plastering)", "per_sqft": Decimal("0.0816")},
    {"id": "aggregate", "name": "Aggregate 20mm", "category": "aggregate", "unit": "tonnes",
     "grade": "20mm blue metal", "per_sqft": Decimal("0.057")},
    {"id": "bricks", "name": "Bricks", "category": "masonry", "unit": "pcs",
     "grade": "Class-A red clay", "per_sqft": Decimal("8.0")},
]


def seed() -> int:
    db = SessionLocal()
    added = 0
    try:
        for m in MATERIALS:
            if db.get(Material, m["id"]) is None:
                db.add(Material(**m))
                added += 1
        db.commit()
    finally:
        db.close()
    print(f"[seed] materials ensured; {added} new")
    return added


if __name__ == "__main__":
    seed()
