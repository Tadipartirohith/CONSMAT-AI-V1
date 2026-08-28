"""Seed demo users for every role (idempotent). Password = settings.demo_password.

org_ref links to the demo entities seeded by site-service (spoke s_medchal, consumer c_demo).
"""
from __future__ import annotations

from .config import settings
from .db import SessionLocal
from .models import User
from . import auth

# (email, name, role, org_ref)
USERS = [
    ("admin@consmat.com", "Platform Admin", "admin", ""),
    ("manager@consmat.com", "Hub Manager", "hub_manager", ""),
    ("supervisor@consmat.com", "Hub Supervisor", "hub_supervisor", ""),
    ("ops@consmat.com", "Hub Operator", "hub_ops", ""),
    ("spoke@consmat.com", "Medchal Spokesperson", "spokesperson", "s_medchal"),
    ("architect@consmat.com", "Site Architect", "architect", "s_medchal"),
    ("site@consmat.com", "Site Engineer", "site_engineer", "s_medchal"),
    ("finance@consmat.com", "Spoke Finance", "finance", "s_medchal"),
    ("demo@consmat.com", "Demo Builder", "consumer", "c_demo"),
    ("vendor@consmat.com", "Deccan Traders", "vendor", "v_deccan"),
]


def seed() -> int:
    db = SessionLocal()
    added = 0
    try:
        pwd = auth.hash_password(settings.demo_password)
        for email, name, role, org_ref in USERS:
            if db.get(User, email) is None:
                db.add(User(id=email, name=name, role=role, org_ref=org_ref, password_hash=pwd))
                added += 1
        db.commit()
    finally:
        db.close()
    print(f"[seed] users ensured; {added} new (password: {settings.demo_password})")
    return added


if __name__ == "__main__":
    seed()
