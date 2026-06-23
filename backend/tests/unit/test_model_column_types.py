"""Guards against model/DB column-type drift.

The integration suite runs on SQLite, which is type-loose and will happily store
a string in a DATE column. PostgreSQL (production) is strict and rejects it, so a
model field mapped as String against a DATE column passes tests but 500s in prod
(this happened with quotations.valid_until). These assertions check the SQLAlchemy
column types directly, independent of the test database.
"""
import sqlalchemy as sa
from app.models.quotation import Quotation
from app.models.amc import AMCContract
from app.models.invoice import Invoice


def _coltype(model, name):
    return type(model.__table__.c[name].type)


def test_date_columns_are_date_typed():
    # Columns backed by a DATE column in the migrations must be Date in the model.
    assert _coltype(Quotation, "valid_until") is sa.Date
    assert _coltype(AMCContract, "start_date") is sa.Date
    assert _coltype(AMCContract, "end_date") is sa.Date
    assert _coltype(Invoice, "invoice_date") is sa.Date
    assert _coltype(Invoice, "due_date") is sa.Date
