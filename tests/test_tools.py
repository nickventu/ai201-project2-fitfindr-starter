from tools import search_listings, suggest_outfit, create_fit_card
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0

def test_search_empty_results():
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []   # empty list, no exception

def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=10)
    assert all(item["price"] <= 10 for item in results)

# ── Mock data ─────────────────────────────────────────────────────────────────

MOCK_NEW_ITEM = {
    "id": "listing_042",
    "title": "Faded Vintage Band Tee",
    "category": "tops",
    "style_tags": ["vintage", "grunge", "graphic"],
    "size": "M",
    "condition": "good",
    "price": 22.0,
    "colors": ["black", "grey"],
    "brand": None,
    "platform": "depop",
    "description": "Washed-out black band tee with cracked graphic print.",
}

MOCK_OUTFIT = (
    "Pair the faded band tee with the high-waisted wide-leg jeans and white "
    "low-top Converse from your wardrobe. Layer the oversized denim jacket on "
    "top for an easy grunge-casual look."
)

SINGLE_ITEM_WARDROBE = {
    "items": [
        {
            "id": "w001",
            "name": "High-Waisted Wide-Leg Jeans",
            "category": "bottoms",
            "colors": ["blue"],
            "style_tags": ["casual", "relaxed"],
            "notes": "90s inspired fit",
        }
    ]
}


# ── suggest_outfit tests ──────────────────────────────────────────────────────

def test_suggest_outfit_with_example_wardrobe():
    wardrobe = get_example_wardrobe()
    result = suggest_outfit(MOCK_NEW_ITEM, wardrobe)
    assert isinstance(result, str)
    assert len(result) > 0


def test_suggest_outfit_with_empty_wardrobe():
    wardrobe = get_empty_wardrobe()
    result = suggest_outfit(MOCK_NEW_ITEM, wardrobe)
    assert isinstance(result, str)
    assert "empty" in result.lower() or "no outfit" in result.lower()


def test_suggest_outfit_with_single_item_wardrobe():
    result = suggest_outfit(MOCK_NEW_ITEM, SINGLE_ITEM_WARDROBE)
    assert isinstance(result, str)
    assert len(result) > 0


# ── create_fit_card tests ─────────────────────────────────────────────────────

def test_create_fit_card_normal():
    result = create_fit_card(MOCK_OUTFIT, MOCK_NEW_ITEM)
    assert isinstance(result, str)
    assert len(result) > 0


def test_create_fit_card_incomplete_outfit():
    result = create_fit_card("", MOCK_NEW_ITEM)
    assert isinstance(result, str)
    # Should prompt the user for more info, not raise
    assert "outfit" in result.lower() or "more" in result.lower()


def test_create_fit_card_missing_new_item():
    result = create_fit_card(MOCK_OUTFIT, {})
    assert isinstance(result, str)
    assert "missing item details" in result.lower()
