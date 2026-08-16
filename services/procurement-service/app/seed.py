"""Seed an initial vendor registry + price lists (idempotent). Run after migrations.

Includes the hub's own supply (is_hub_self) plus a few external vendors carried from V0, so the
market view and later procurement selection have realistic data. Usage: python -m app.seed
"""
from __future__ import annotations

from decimal import Decimal

from .db import SessionLocal
from .models import Vendor, VendorPrice

# (vendor_id, name, city, is_hub_self, {material_id: price})
VENDORS = [
    ("v_hub", "Consmat Hub Supply", "Hyderabad", True,
     {"cement": 420, "steel": 63500, "sand": 1100, "aggregate": 1050, "bricks": 7.5}),
    ("v_deccan", "Deccan Traders", "Medchal", False,
     {"cement": 415, "steel": 64500}),
    ("v_metro", "Metro Steel & Cement", "Sangareddy", False,
     {"cement": 402, "steel": 62900, "aggregate": 980}),
    ("v_godavari", "Godavari Sand Co.", "Ibrahimpatnam", False,
     {"sand": 1080, "aggregate": 1010}),
    ("v_kakatiya", "Kakatiya Bricks Mfg.", "Bhongir", False,
     {"bricks": 7.2, "aggregate": 1120}),
]


def seed() -> int:
    db = SessionLocal()
    added = 0
    try:
        for vid, name, city, is_hub, prices in VENDORS:
            v = db.get(Vendor, vid)
            if v is None:
                v = Vendor(id=vid, name=name, city=city, is_hub_self=is_hub, active=True)
                db.add(v)
                db.flush()
                added += 1
            for mid, price in prices.items():
                exists = any(p.material_id == mid for p in v.prices)
                if not exists:
                    db.add(VendorPrice(vendor_id=vid, material_id=mid, price=Decimal(str(price))))
        db.commit()
    finally:
        db.close()
    print(f"[seed] vendors ensured; {added} new")
    return added


if __name__ == "__main__":
    seed()
