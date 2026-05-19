import pytest

from services.manual_live_pilot_review_service_v2 import ManualLivePilotReviewServiceV2


class FakeCursor:
    def __init__(self, docs):
        self.docs = docs

    def sort(self, key, direction=1):
        self.docs = sorted(self.docs, key=lambda item: item.get(key, ""), reverse=direction == -1)
        return self

    def limit(self, limit):
        self.docs = self.docs[:limit]
        return self

    async def to_list(self, limit):
        return self.docs[:limit]


class FakeCollection:
    def __init__(self):
        self.docs = []

    async def insert_one(self, doc):
        self.docs.append(dict(doc))

    async def update_one(self, query, update, upsert=False):
        target = None
        for doc in self.docs:
            if all(doc.get(k) == v for k, v in query.items()):
                target = doc
                break
        if target is None:
            if not upsert:
                return
            target = dict(query)
            for key, value in update.get("$setOnInsert", {}).items():
                target[key] = value
            self.docs.append(target)
        for key, value in update.get("$set", {}).items():
            target[key] = value

    async def find_one(self, query, projection=None, sort=None):
        def value_for(doc, dotted_key):
            value = doc
            for part in dotted_key.split("."):
                if not isinstance(value, dict):
                    return None
                value = value.get(part)
            return value

        matches = [dict(doc) for doc in self.docs if all(value_for(doc, key) == value for key, value in query.items())]
        if sort:
            for key, direction in reversed(sort):
                matches = sorted(matches, key=lambda item: item.get(key, ""), reverse=direction == -1)
        return matches[0] if matches else None

    def find(self, query, projection=None):
        return FakeCursor([dict(doc) for doc in self.docs if all(doc.get(key) == value for key, value in query.items())])


class FakeDB:
    def __init__(self):
        self.manual_live_pilot_reports = FakeCollection()
        self.manual_live_pilot_signoffs = FakeCollection()
        self.live_post_submit_reconciliation_requirements = FakeCollection()
        self.alerts = FakeCollection()


@pytest.mark.asyncio
async def test_review_status_requires_signoff_for_complete_report():
    db = FakeDB()
    await db.manual_live_pilot_reports.insert_one({
        "user_id": "user-1",
        "live_order_id": "order-1",
        "status": "complete",
        "generated_at": "2026-01-01T00:00:00+00:00",
        "report_hash": "report-hash-1",
    })

    result = await ManualLivePilotReviewServiceV2(db).expansion_status("user-1")

    assert result["allowed_to_repeat_pilot"] is False
    assert result["blockers"][0]["name"] == "completed_pilot_report_without_signoff"


@pytest.mark.asyncio
async def test_signoff_requires_reconciliation_to_be_resolved():
    db = FakeDB()
    await db.manual_live_pilot_reports.insert_one({
        "user_id": "user-1",
        "live_order_id": "order-1",
        "status": "complete",
        "generated_at": "2026-01-01T00:00:00+00:00",
        "report_hash": "report-hash-1",
    })
    await db.live_post_submit_reconciliation_requirements.insert_one({
        "user_id": "user-1",
        "live_order_id": "order-1",
        "status": "pending",
        "created_at": "2026-01-01T00:00:00+00:00",
    })

    result = await ManualLivePilotReviewServiceV2(db).signoff_report(
        user_id="user-1",
        live_order_id="order-1",
        operator_id="operator-1",
        decision="hold",
    )

    assert result["success"] is False
    assert result["status"] == "pending_reconciliation"


@pytest.mark.asyncio
async def test_signoff_record_clears_review_status():
    db = FakeDB()
    await db.manual_live_pilot_reports.insert_one({
        "user_id": "user-1",
        "live_order_id": "order-1",
        "status": "complete",
        "generated_at": "2026-01-01T00:00:00+00:00",
        "report_hash": "report-hash-1",
    })
    await db.live_post_submit_reconciliation_requirements.insert_one({
        "user_id": "user-1",
        "live_order_id": "order-1",
        "status": "resolved",
        "created_at": "2026-01-01T00:00:00+00:00",
    })

    service = ManualLivePilotReviewServiceV2(db)
    signoff = await service.signoff_report(
        user_id="user-1",
        live_order_id="order-1",
        operator_id="operator-1",
        decision="hold",
        notes="reviewed",
    )
    status = await service.expansion_status("user-1")

    assert signoff["success"] is True
    assert signoff["signoff"]["signoff_hash"]
    assert status["allowed_to_repeat_pilot"] is True
    assert status["blockers"] == []


@pytest.mark.asyncio
async def test_reconciliation_alerts_are_not_duplicated():
    db = FakeDB()
    await db.live_post_submit_reconciliation_requirements.insert_one({
        "user_id": "user-1",
        "live_order_id": "order-1",
        "status": "pending",
        "created_at": "2026-01-01T00:00:00+00:00",
    })

    service = ManualLivePilotReviewServiceV2(db)
    first = await service.emit_unresolved_reconciliation_alerts("user-1")
    second = await service.emit_unresolved_reconciliation_alerts("user-1")

    assert first["alerts_emitted"] == 1
    assert second["alerts_emitted"] == 0
    assert db.alerts.docs[0]["type"] == "manual_live_unresolved_reconciliation"
