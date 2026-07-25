import app.db.provenance_repository as provenance_repository_module
from app.db.provenance_repository import JsonFileProvenanceEventRepository


def _isolated_repo(tmp_path, monkeypatch):
    events_file = tmp_path / "provenance_events.json"
    monkeypatch.setattr(provenance_repository_module, "PROVENANCE_EVENTS_FILE", events_file)
    return JsonFileProvenanceEventRepository()


def test_append_and_list_round_trip(tmp_path, monkeypatch):
    repo = _isolated_repo(tmp_path, monkeypatch)
    repo.append_event("p1", "buying_price", "rejected", "looked wrong", "user")
    events = repo.list_events("p1")
    assert len(events) == 1
    assert events[0].event_type == "rejected"
    assert events[0].field_key == "buying_price"


def test_events_are_scoped_per_profile(tmp_path, monkeypatch):
    repo = _isolated_repo(tmp_path, monkeypatch)
    repo.append_event("p1", "buying_price", "rejected", None, "user")
    repo.append_event("p2", "buying_price", "rejected", None, "user")
    assert len(repo.list_events("p1")) == 1
    assert len(repo.list_events("p2")) == 1


def test_events_are_returned_in_chronological_order(tmp_path, monkeypatch):
    repo = _isolated_repo(tmp_path, monkeypatch)
    repo.append_event("p1", "buying_price", "rejected", None, "user")
    repo.append_event("p1", "buying_price", "rejection_cleared", None, "user")
    events = repo.list_events("p1")
    assert [e.event_type for e in events] == ["rejected", "rejection_cleared"]


def test_no_events_returns_empty_list(tmp_path, monkeypatch):
    repo = _isolated_repo(tmp_path, monkeypatch)
    assert repo.list_events("nonexistent") == []
