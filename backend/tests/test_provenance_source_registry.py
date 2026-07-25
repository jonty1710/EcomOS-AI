from app.provenance.source_registry import SOURCE_REGISTRY


def test_all_seven_examples_from_brief_are_registered():
    expected = {"marketplace", "manufacturer", "supplier", "user", "calculation_engine", "knowledge_engine", "ai_provider"}
    assert expected.issubset(SOURCE_REGISTRY.keys())


def test_all_reliability_scores_are_valid_probabilities():
    for source in SOURCE_REGISTRY.values():
        assert 0.0 <= source.baseline_reliability <= 1.0


def test_calculation_engine_has_maximum_reliability():
    assert SOURCE_REGISTRY["calculation_engine"].baseline_reliability == 1.0


def test_ai_provider_has_lowest_reliability_matching_prs_evidence_hierarchy():
    # PRS §5: AI reasoning is the weakest evidence tier by design.
    ai = SOURCE_REGISTRY["ai_provider"].baseline_reliability
    assert ai < min(s.baseline_reliability for k, s in SOURCE_REGISTRY.items() if k != "ai_provider")


def test_every_entry_has_a_non_empty_description():
    for source in SOURCE_REGISTRY.values():
        assert source.description.strip()
