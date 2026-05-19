import importlib


def test_api_routes_v3_imports_and_exposes_pilot_routes():
    module = importlib.import_module("api_routes_v3")
    routes = {route.path for route in module.api_router.routes}

    expected = {
        "/live-trading/pilot-readiness",
        "/live-trading/pilot/pending-reconciliation",
        "/live-trading/pilot/resolve-reconciliation",
        "/live-trading/pilot/report",
        "/live-trading/pilot/reports",
        "/live-trading/pilot/expansion-status",
        "/live-trading/pilot/signoff",
        "/live-trading/pilot/signoffs",
        "/live-trading/pilot/unresolved-reconciliation-alerts",
    }

    assert expected.issubset(routes)


def test_phase5_to_phase8_services_import_cleanly():
    modules = [
        "services.manual_live_pilot_readiness_service_v2",
        "services.manual_live_pilot_workflow_service_v2",
        "services.manual_live_pilot_review_service_v2",
        "services.live_manual_order_lifecycle_service_v2",
        "services.live_trading_service_v2",
    ]

    for module_name in modules:
        assert importlib.import_module(module_name)
