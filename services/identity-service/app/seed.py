"""Seed demo users for every role (idempotent). Password = settings.demo_password.

org_ref links to the demo entities seeded by site-service (spoke s_medchal, consumer c_demo).
"""
from __future__ import annotations

from sqlalchemy import select

from .config import settings
from .db import SessionLocal
from .models import Team, TeamMember, User
from . import auth

# (email, name, role, org_ref)
USERS = [
    ("admin@consmat.com", "Platform Admin", "admin", ""),
    ("manager@consmat.com", "Hub Manager", "hub_manager", ""),
    ("hr@consmat.com", "People Ops", "hr", ""),
    ("supervisor@consmat.com", "Hub Supervisor", "hub_supervisor", ""),
    ("ops@consmat.com", "Hub Operator", "hub_ops", ""),
    ("spoke@consmat.com", "Medchal Spokesperson", "spokesperson", "s_medchal"),
    ("architect@consmat.com", "Site Architect", "architect", "s_medchal"),
    ("site@consmat.com", "Site Engineer", "site_engineer", "s_medchal"),
    ("finance@consmat.com", "Spoke Finance", "finance", "s_medchal"),
    ("demo@consmat.com", "Demo Builder", "consumer", "c_demo"),
    ("vendor@consmat.com", "Deccan Traders", "vendor", "v_deccan"),
]

# One demo team (OpenStack-style project) so the feature is visible on first boot.
# (team name, description, spoke_id, [(user_email, team_role)])
DEMO_TEAMS = [
    ("Medchal Field Pod", "Field execution team for the Medchal branch.", "s_medchal",
     [("site@consmat.com", "admin"), ("architect@consmat.com", "member"), ("finance@consmat.com", "viewer")]),
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
        # Seed demo teams only when none exist yet (idempotent, non-destructive).
        if db.execute(select(Team).limit(1)).scalar_one_or_none() is None:
            for name, desc, spoke, members in DEMO_TEAMS:
                t = Team(name=name, description=desc, spoke_id=spoke)
                db.add(t)
                db.flush()
                for email, trole in members:
                    if db.get(User, email) is not None:
                        db.add(TeamMember(team_id=t.id, user_id=email, role=trole, granted_by="seed"))
            db.commit()
            print(f"[seed] demo team(s) created: {[t[0] for t in DEMO_TEAMS]}")
    finally:
        db.close()
    print(f"[seed] users ensured; {added} new (password: {settings.demo_password})")
    return added


if __name__ == "__main__":
    seed()
