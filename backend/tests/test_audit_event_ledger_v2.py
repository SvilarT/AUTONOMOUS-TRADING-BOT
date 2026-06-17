import pytest

from services.audit_event_ledger_v2 import AuditEventLedgerV2


class FakeCursor:
    def __init__(self, docs):
        self.docs = list(docs)

    def sort(self, key, direction):
        self.docs.sort(key=lambda item: item.get(key), reverse=direction < 0)
        return self

    def limit(self, limit):
        self.docs = self.docs[:limit]
        return self

    async def to_list(self, length):
        return self.docs[:length]


class FakeCollection:
    def __init__(self):
        self.docs = []

    async def create_index(self, *args, **kwargs):
        return None

    async def insert_one(self, doc):
        self.docs.append(dict(doc))

    async def find_one(self, query, projection=None, sort=None):
        matches = [doc for doc in self.docs if all(doc.get(key) == value for key, value in query.items())]
        if sort:
            for key, direction in reversed(sort):
                matches.sort(key=lambda item: item.get(key), reverse=direction < 0)
        return dict(matches[0]) if matches else None

    def find(self, query, projection=None):
        matches = [doc for doc in self.docs if all(doc.get(key) == value for key, value in query.items())]
        return FakeCursor(matches)


class FakeDb:
    def __init__(self):
        self.audit_events_v2 = FakeCollection()


@pytest.mark.asyncio
async def test_audit_event_ledger_appends_and_verifies_chain():
    ledger = AuditEventLedgerV2(FakeDb())

    first = await ledger.append(
        user_id="u1",
        stream_id="u1:BTC-USD",
        event_type="SignalGenerated",
        payload={"symbol": "BTC-USD", "action": "BUY"},
        correlation_id="c1",
    )
    second = await ledger.append(
        user_id="u1",
        stream_id="u1:BTC-USD",
        event_type="RiskCheckPassed",
        payload={"decision": "allow"},
        correlation_id="c1",
    )

    assert second["previous_hash"] == first["event_hash"]
    events = await ledger.load_stream("u1:BTC-USD")
    assert [event["sequence"] for event in events] == [1, 2]

    verification = await ledger.verify_user_chain("u1")
    assert verification["valid"] is True
    assert verification["checked"] == 2
