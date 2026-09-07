from types import SimpleNamespace

from python.auto_healing.healer import SUPPORTED_CHECKS, heal_run_once


class FakeConnection:
    def __init__(self, checks):
        self.checks = checks
        self.actions = []

    def execute(self, statement, params=None):
        sql = str(statement)
        if "FROM observability.data_quality_results" in sql:
            return SimpleNamespace(all=lambda: [SimpleNamespace(check_name=c) for c in self.checks])
        if "INSERT INTO observability.healing_actions" in sql:
            self.actions.append(params)
            return None
        raise AssertionError(f"Unexpected SQL: {sql}")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class FakeEngine:
    def __init__(self, checks):
        self.connection = FakeConnection(checks)

    def begin(self):
        return self.connection

    def dispose(self):
        pass


def test_no_failed_checks_is_skipped():
    engine = FakeEngine([])

    assert heal_run_once("run-1", engine=engine) == "skipped"
    assert engine.connection.actions[0]["action_name"] == "quality_gate"


def test_gold_failure_records_refresh_action():
    engine = FakeEngine(["gold_has_rows"])

    assert heal_run_once("run-1", engine=engine) == "success"
    assert engine.connection.actions[0]["action_name"] == "gold_table_refresh_required"


def test_unknown_failure_is_manual_review():
    engine = FakeEngine(["new_check"])

    assert heal_run_once("run-1", engine=engine) == "success"
    assert engine.connection.actions[0]["action_name"] == "manual_review_new_check"


def test_supported_checks_are_explicit():
    assert SUPPORTED_CHECKS == {"gold_has_rows", "bronze_min_records"}
