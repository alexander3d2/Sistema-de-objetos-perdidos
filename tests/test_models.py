from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from models import User, Item
from extensions import db

def test_user_password_hashing(client):
    u = User(username="abc", email="abc@test.com")
    u.set_password("secret123")
    assert u.check_password("secret123")
    assert not u.check_password("wrong")

def test_create_item(client):
    item = Item(
        name="Test Product",
        description="demo",
        category="Electronics",
    )
    db.session.add(item)
    db.session.commit()

    assert item.id is not None
    assert not hasattr(item, "quantity")
    assert not hasattr(item, "price")


def test_lost_object_fields_default_to_lost_without_details(client):
    item = Item(name="Paraguas")
    db.session.add(item)
    db.session.commit()
    db.session.refresh(item)

    assert item.status == "lost"
    assert item.location is None
    assert item.event_date is None
    assert item.contact is None


def test_lost_object_fields_round_trip(client):
    item = Item(
        name="Llaves",
        category="keys",
        location="Biblioteca central",
        event_date=date(2026, 3, 15),
        status="found",
        contact="ana@universidad.edu",
    )
    db.session.add(item)
    db.session.commit()
    db.session.expire_all()

    stored = db.session.get(Item, item.id)
    assert stored.location == "Biblioteca central"
    assert stored.event_date == date(2026, 3, 15)
    assert stored.status == "found"
    assert stored.contact == "ana@universidad.edu"


def test_status_column_is_required_with_a_database_default(client):
    column = Item.__table__.c.status
    assert column.nullable is False
    assert column.server_default is not None
    assert column.server_default.arg == "lost"

    # The ORM substitutes its default for None, so check the constraint with raw SQL.
    with pytest.raises(IntegrityError):
        db.session.execute(db.text("INSERT INTO item (name, status) VALUES ('Mochila', NULL)"))
    db.session.rollback()

    db.session.execute(db.text("INSERT INTO item (name) VALUES ('Mochila')"))
    assert db.session.execute(db.text("SELECT status FROM item")).scalar_one() == "lost"
    db.session.rollback()


def test_new_optional_columns_are_nullable(client):
    for name in ("location", "event_date", "contact"):
        assert Item.__table__.c[name].nullable is True


def test_item_status_helpers(client):
    assert Item(name="a", status="returned").is_returned is True
    assert Item(name="b", status="lost").is_returned is False
    assert Item(name="c", status="found").status_label == "Encontrado"
    assert Item(name="d", status="legacy").status_label == "legacy"
