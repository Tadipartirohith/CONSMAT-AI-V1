"""Seed the materials reference data (idempotent). Run after migrations.

Usage: python -m app.seed
"""
from __future__ import annotations

from decimal import Decimal

from .db import SessionLocal
from .models import Material, Product

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


# Branded products (several companies per material) — the searchable catalog.
def _p(pid, material, brand, name, grade, unit):
    return {"id": pid, "material_id": material, "brand": brand, "name": name, "grade": grade, "unit": unit}


PRODUCTS = [
    _p("cement-ultratech-opc53", "cement", "UltraTech", "UltraTech OPC 53 Grade Cement 50kg", "OPC 53", "bags"),
    _p("cement-acc-gold-ppc", "cement", "ACC", "ACC Gold Water Shield PPC Cement 50kg", "PPC", "bags"),
    _p("cement-ambuja-plus", "cement", "Ambuja", "Ambuja Plus Roof Special PPC Cement 50kg", "PPC", "bags"),
    _p("cement-dalmia-dsp", "cement", "Dalmia", "Dalmia DSP OPC 43 Grade Cement 50kg", "OPC 43", "bags"),
    _p("cement-bharathi-opc", "cement", "Bharathi", "Bharathi Cement OPC 53 Grade 50kg", "OPC 53", "bags"),
    _p("steel-tata-tiscon", "steel", "TATA", "TATA Tiscon 500D TMT Bar", "Fe 500D", "tonnes"),
    _p("steel-jsw-neosteel", "steel", "JSW", "JSW Neosteel 550D TMT Bar", "Fe 550D", "tonnes"),
    _p("steel-sail-tmt", "steel", "SAIL", "SAIL TMT Fe 500 Bar", "Fe 500", "tonnes"),
    _p("sand-river-fine", "sand", "", "River Sand (Fine, plastering grade)", "Fine", "tonnes"),
    _p("sand-msand", "sand", "", "Manufactured Sand (M-Sand) for concrete", "M-Sand", "tonnes"),
    _p("aggregate-20mm-blue", "aggregate", "", "20mm Blue Metal Aggregate", "20mm", "tonnes"),
    _p("aggregate-12mm", "aggregate", "", "12mm Crushed Stone Aggregate", "12mm", "tonnes"),
    _p("bricks-redclay-a", "bricks", "", "Class-A Red Clay Bricks", "Class-A", "pcs"),
    _p("bricks-aac-block", "bricks", "", "AAC Lightweight Block 600x200x100", "AAC", "pcs"),
    _p("bricks-flyash", "bricks", "", "Fly Ash Bricks", "Fly Ash", "pcs"),
]


def seed() -> int:
    db = SessionLocal()
    added = 0
    try:
        for m in MATERIALS:
            if db.get(Material, m["id"]) is None:
                db.add(Material(**m))
                added += 1
        for p in PRODUCTS:
            if db.get(Product, p["id"]) is None:
                db.add(Product(**p))
        db.commit()
    finally:
        db.close()
    print(f"[seed] materials + products ensured; {added} new materials")
    return added


if __name__ == "__main__":
    seed()
