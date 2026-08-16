"""Seed an initial vendor registry + product-level price lists (idempotent). Run after migrations.

Several companies compete per material (e.g. UltraTech / ACC / Ambuja / Dalmia / Bharathi cement).
Prices are keyed by product (brand SKU) and carry denormalized material/brand/name from the catalog.
Usage: python -m app.seed
"""
from __future__ import annotations

from decimal import Decimal

from .db import SessionLocal
from .models import Vendor, VendorPrice

# product_id -> (material_id, brand, full name) — mirrors the inventory catalog seed.
PRODUCTS = {
    "cement-ultratech-opc53": ("cement", "UltraTech", "UltraTech OPC 53 Grade Cement 50kg"),
    "cement-acc-gold-ppc": ("cement", "ACC", "ACC Gold Water Shield PPC Cement 50kg"),
    "cement-ambuja-plus": ("cement", "Ambuja", "Ambuja Plus Roof Special PPC Cement 50kg"),
    "cement-dalmia-dsp": ("cement", "Dalmia", "Dalmia DSP OPC 43 Grade Cement 50kg"),
    "cement-bharathi-opc": ("cement", "Bharathi", "Bharathi Cement OPC 53 Grade 50kg"),
    "steel-tata-tiscon": ("steel", "TATA", "TATA Tiscon 500D TMT Bar"),
    "steel-jsw-neosteel": ("steel", "JSW", "JSW Neosteel 550D TMT Bar"),
    "steel-sail-tmt": ("steel", "SAIL", "SAIL TMT Fe 500 Bar"),
    "sand-river-fine": ("sand", "", "River Sand (Fine, plastering grade)"),
    "sand-msand": ("sand", "", "Manufactured Sand (M-Sand) for concrete"),
    "aggregate-20mm-blue": ("aggregate", "", "20mm Blue Metal Aggregate"),
    "aggregate-12mm": ("aggregate", "", "12mm Crushed Stone Aggregate"),
    "bricks-redclay-a": ("bricks", "", "Class-A Red Clay Bricks"),
    "bricks-flyash": ("bricks", "", "Fly Ash Bricks"),
}

VENDORS = [
    ("v_hub", "Consmat Hub Supply", "Hyderabad", True),
    ("v_deccan", "Deccan Traders", "Medchal", False),
    ("v_metro", "Metro Steel & Cement", "Sangareddy", False),
    ("v_godavari", "Godavari Sand Co.", "Ibrahimpatnam", False),
    ("v_kakatiya", "Kakatiya Bricks Mfg.", "Bhongir", False),
]

# (vendor_id, product_id, price)
PRICES = [
    ("v_hub", "cement-ultratech-opc53", 420), ("v_hub", "steel-tata-tiscon", 63500),
    ("v_hub", "sand-river-fine", 1100), ("v_hub", "aggregate-20mm-blue", 1050), ("v_hub", "bricks-redclay-a", 7.5),
    ("v_deccan", "cement-ultratech-opc53", 415), ("v_deccan", "cement-acc-gold-ppc", 425),
    ("v_deccan", "cement-dalmia-dsp", 388), ("v_deccan", "steel-tata-tiscon", 64500),
    ("v_metro", "cement-acc-gold-ppc", 402), ("v_metro", "cement-ambuja-plus", 410),
    ("v_metro", "cement-bharathi-opc", 375), ("v_metro", "steel-sail-tmt", 62900),
    ("v_metro", "aggregate-20mm-blue", 980),
    ("v_godavari", "sand-river-fine", 1080), ("v_godavari", "sand-msand", 1050),
    ("v_godavari", "aggregate-20mm-blue", 1010),
    ("v_kakatiya", "bricks-redclay-a", 7.2), ("v_kakatiya", "bricks-flyash", 6.5),
    ("v_kakatiya", "aggregate-20mm-blue", 1120),
]


def seed() -> int:
    db = SessionLocal()
    added = 0
    try:
        for vid, name, city, is_hub in VENDORS:
            if db.get(Vendor, vid) is None:
                db.add(Vendor(id=vid, name=name, city=city, is_hub_self=is_hub, active=True))
                added += 1
        db.flush()
        existing = {(p.vendor_id, p.product_id) for p in db.query(VendorPrice).all()}
        for vid, pid, price in PRICES:
            if (vid, pid) in existing:
                continue
            material, brand, pname = PRODUCTS[pid]
            db.add(VendorPrice(vendor_id=vid, product_id=pid, material_id=material, brand=brand,
                               product_name=pname, price=Decimal(str(price))))
        db.commit()
    finally:
        db.close()
    print(f"[seed] vendors ensured ({added} new) + product price lists")
    return added


if __name__ == "__main__":
    seed()
