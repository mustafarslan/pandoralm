from pytest_archon import archrule


def test_services_should_not_import_api():
    """
    Services (Business Logic) should never depend on API (Interface Layer).
    Dependnecy direction: API -> Services
    """
    (
        archrule("services_isolation")
        .exclude("tests")
        .match("app.services*")
        .should_not_import("app.api*")
        .check("app")
    )

def test_core_should_not_import_external_infrastructure():
    """
    Core domain logic should remain independent of heavy infrastructure code
    located in workers or direct DB drivers (use interfaces instead).
    """
    (
        archrule("core_onion_architecture")
        .exclude("tests")
        .match("app.core*")
        .should_not_import("app.workers*")
        .check("app")
    )

def test_router_should_be_isolated():
    """
    The cognitive router is a critical component and should not have
    dependencies on specific vector stores or graph implementations directly.
    It should use abstractions.
    """
    (
        archrule("router_abstraction")
        .exclude("tests")
        .match("app.services.router*")
        .should_not_import("lancedb")
        .should_not_import("neo4j")
        .check("app")
    )
