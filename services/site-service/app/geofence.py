"""Geofence resolution (Q7): map a free-text location to the serving spoke by area keyword.

A spoke covers one or more area keywords (e.g. "medchal"). A location string is served by the spoke
whose covered area appears in it; when several match, the most specific (longest) keyword wins.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models


def resolve_spoke(db: Session, location: str) -> models.Spoke | None:
    if not location or not location.strip():
        return None
    loc = location.lower()
    rows = db.execute(
        select(models.SpokeArea).join(models.Spoke).where(models.Spoke.active.is_(True))
    ).scalars().all()
    matches = [(r.spoke_id, r.area) for r in rows if r.area.lower() in loc]
    if not matches:
        return None
    matches.sort(key=lambda m: len(m[1]), reverse=True)  # most specific keyword first
    return db.get(models.Spoke, matches[0][0])
