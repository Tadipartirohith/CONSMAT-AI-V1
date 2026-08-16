"""Unit tests for the config-driven payment adapter + domain logic (mock provider)."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app import service, models, payments


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    s = Session()
    yield s
    s.close()


def test_mock_provider_settles_immediately():
    result = payments.charge(1000)
    assert result["provider"] == "mock"
    assert result["status"] == models.PAID
    assert result["provider_ref"].startswith("mock_")


def test_create_payment_paid(db):
    pay = service.create_payment(db, ref="SITE-1", consumer_id="c_demo", amount=396976)
    assert pay.status == "paid"
    assert pay.code == "PAY-1"
    assert pay.currency == "INR"
    assert pay.paid_at is not None


def test_amount_must_be_positive(db):
    with pytest.raises(service.PaymentError):
        service.create_payment(db, ref="SITE-1", consumer_id="c_demo", amount=0)


def test_list_filters_by_consumer(db):
    service.create_payment(db, ref="SITE-1", consumer_id="c_demo", amount=100)
    service.create_payment(db, ref="SITE-2", consumer_id="c_other", amount=200)
    mine = service.list_payments(db, consumer_id="c_demo")
    assert len(mine) == 1
    assert mine[0].ref == "SITE-1"
