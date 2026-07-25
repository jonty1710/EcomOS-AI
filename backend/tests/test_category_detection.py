from app.research.category_detection import detect_category


def test_detects_kitchen_category():
    result = detect_category("Stainless Steel Kitchen Storage Container")
    assert result.category == "Kitchen & Dining"
    assert result.categorization_confidence > 0.5


def test_uncategorized_when_no_keywords_match():
    result = detect_category("Xyzzy Plugh Foobar")
    assert result.category == "Uncategorized"
    assert result.categorization_confidence < 0.2


def test_category_hint_is_authoritative():
    result = detect_category("Random Product", category_hint="Fitness & Sports")
    assert result.category == "Fitness & Sports"
    assert result.categorization_confidence == 1.0
