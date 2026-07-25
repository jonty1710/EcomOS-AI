import app.db.profile_repository as profile_repository_module
from app.collection.collector import collect
from app.db.profile_repository import JsonFileProfileRepository


def _isolated_repo(tmp_path, monkeypatch):
    profiles_file = tmp_path / "profiles.json"
    monkeypatch.setattr(profile_repository_module, "PROFILES_FILE", profiles_file)
    return JsonFileProfileRepository()


def test_create_and_get_round_trip(tmp_path, monkeypatch):
    repo = _isolated_repo(tmp_path, monkeypatch)
    profile = collect("s1", {"product_name": "X", "selling_price": 100, "buying_price": 50,
                              "shipping_cost": 5, "packaging_cost": 5, "supplier_name": "Y", "weight_grams": 100})
    repo.create_profile(profile)
    fetched = repo.get_profile(profile.id)
    assert fetched is not None
    assert fetched.product_name == "X"


def test_versioning_hides_superseded_from_list(tmp_path, monkeypatch):
    repo = _isolated_repo(tmp_path, monkeypatch)
    v1 = collect("s1", {"product_name": "X", "selling_price": 100})
    repo.create_profile(v1)
    v2 = collect("s1", {"product_name": "X", "selling_price": 150}, version=2, previous_version_id=v1.id)
    repo.create_profile(v2)

    summaries = repo.list_profiles(session_id="s1")
    ids = [s.id for s in summaries]
    assert v2.id in ids
    assert v1.id not in ids  # superseded, hidden from the main list

    history = repo.list_versions(v2.id)
    assert [h.id for h in history] == [v2.id, v1.id]


def test_delete_profile(tmp_path, monkeypatch):
    repo = _isolated_repo(tmp_path, monkeypatch)
    profile = collect("s1", {"product_name": "X"})
    repo.create_profile(profile)
    assert repo.delete_profile(profile.id) is True
    assert repo.get_profile(profile.id) is None
    assert repo.delete_profile(profile.id) is False
