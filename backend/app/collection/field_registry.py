"""The field registry — the single canonical list of every field the Data
Collection Engine knows about. This is deliberately the ONLY place field
metadata is declared; validation.py, calculations.py, quality_score.py, and
the frontend (via GET /api/v1/collection/field-registry) all read from this,
never redeclare it.

Why `collection_type` and `requires_manual_verification` are separate fields
rather than folding "Manual Verification Required" into one 3-way enum (even
though the Phase 2 brief's GOAL section lists it as a peer of Auto Detect /
User Input Required): the brief's own worked examples show a field can be
BOTH e.g. Buying Price is "Collection Type: Manual Input, Verification
Required: Yes" — verification-required is a property that can attach to
either an auto-detected or a user-entered value, not a mutually exclusive
third source. Modeling it as an orthogonal flag lets Buying Price be
"user_input + requires_verification" without inventing a fourth combinatorial
enum value. `EffectiveClassification` (schemas.py) is what collapses these
two into the single display bucket the UI shows, with verification-required
taking priority — see collector.py `effective_classification_for`.

Why several fields below are `AUTO_DETECT` even though nothing in Phase 2
can actually auto-detect them yet (no connector exists): `collection_type`
records the field's PERMANENT policy — what should populate it once a
connector is wired in (Phase 3+). It is not a claim that detection is
available today. The Data Collector (collector.py) is what decides, at
collection time, whether an auto-detect field currently has a real source;
today the only real one is Category (a genuine deterministic keyword
classifier, reused from Phase 1). Every other AUTO_DETECT field falls
through to "ask the user" honestly, never a guess.
"""

from app.collection.schemas import CollectionType, DataType, FieldDefinition

SECTION_BASIC = "Basic Product Information"
SECTION_PRICING = "Pricing"
SECTION_PHYSICAL = "Physical Attributes"
SECTION_MARKET = "Market Information"
SECTION_SUPPLIER = "Supplier"

SECTIONS = [SECTION_BASIC, SECTION_PRICING, SECTION_PHYSICAL, SECTION_MARKET, SECTION_SUPPLIER]

_REGISTRY_LIST: list[FieldDefinition] = [
    # --- Section 1: Basic Product Information ---------------------------------
    FieldDefinition(
        key="product_name", label="Product Name", section=SECTION_BASIC,
        data_type=DataType.TEXT, collection_type=CollectionType.USER_INPUT,
        required=True, source_hint="User",
    ),
    FieldDefinition(
        key="brand", label="Brand", section=SECTION_BASIC,
        data_type=DataType.TEXT, collection_type=CollectionType.AUTO_DETECT,
        required=False, source_hint="Marketplace",
    ),
    FieldDefinition(
        key="category", label="Category", section=SECTION_BASIC,
        data_type=DataType.TEXT, collection_type=CollectionType.AUTO_DETECT,
        required=False, source_hint="Deterministic keyword match",
        help_text="Auto-detected from the product name using a fixed keyword taxonomy (no AI).",
    ),
    FieldDefinition(
        key="sub_category", label="Sub Category", section=SECTION_BASIC,
        data_type=DataType.TEXT, collection_type=CollectionType.AUTO_DETECT,
        required=False, source_hint="Deterministic keyword match",
    ),
    FieldDefinition(
        key="sku", label="SKU", section=SECTION_BASIC,
        data_type=DataType.TEXT, collection_type=CollectionType.USER_INPUT,
        required=False, source_hint="User",
    ),
    FieldDefinition(
        key="variant", label="Variant", section=SECTION_BASIC,
        data_type=DataType.TEXT, collection_type=CollectionType.USER_INPUT,
        required=False, source_hint="User",
    ),
    FieldDefinition(
        key="model_number", label="Model Number", section=SECTION_BASIC,
        data_type=DataType.TEXT, collection_type=CollectionType.USER_INPUT,
        required=False, source_hint="User",
    ),
    FieldDefinition(
        key="hsn_code", label="HSN Code", section=SECTION_BASIC,
        data_type=DataType.TEXT, collection_type=CollectionType.USER_INPUT,
        required=False, requires_manual_verification=True, source_hint="User",
        help_text="Optional, but affects GST classification — confirm with a compliance professional.",
    ),
    # --- Section 2: Pricing -----------------------------------------------------
    FieldDefinition(
        key="mrp", label="MRP", section=SECTION_PRICING,
        data_type=DataType.NUMBER, collection_type=CollectionType.USER_INPUT,
        required=False, source_hint="User", unit="currency", min_value=0,
    ),
    FieldDefinition(
        key="selling_price", label="Selling Price", section=SECTION_PRICING,
        data_type=DataType.NUMBER, collection_type=CollectionType.AUTO_DETECT,
        required=True, source_hint="Marketplace", unit="currency", min_value=0,
    ),
    FieldDefinition(
        key="discount_pct", label="Discount %", section=SECTION_PRICING,
        data_type=DataType.NUMBER, collection_type=CollectionType.CALCULATED,
        source_hint="Deterministic", unit="percent",
        help_text="(MRP - Selling Price) / MRP — only computed if MRP is provided.",
    ),
    FieldDefinition(
        key="buying_price", label="Buying Price", section=SECTION_PRICING,
        data_type=DataType.NUMBER, collection_type=CollectionType.USER_INPUT,
        required=True, requires_manual_verification=True, source_hint="Supplier",
        unit="currency", min_value=0,
    ),
    FieldDefinition(
        key="gst_pct", label="GST %", section=SECTION_PRICING,
        data_type=DataType.NUMBER, collection_type=CollectionType.USER_INPUT,
        required=False, source_hint="User", unit="percent", min_value=0, max_value=100,
    ),
    FieldDefinition(
        key="marketplace_fee_pct", label="Marketplace Fees", section=SECTION_PRICING,
        data_type=DataType.NUMBER, collection_type=CollectionType.AUTO_DETECT,
        required=False, source_hint="Marketplace fee schedule", unit="percent", min_value=0, max_value=100,
    ),
    FieldDefinition(
        key="closing_fee", label="Closing Fees", section=SECTION_PRICING,
        data_type=DataType.NUMBER, collection_type=CollectionType.USER_INPUT,
        required=False, source_hint="User", unit="currency", min_value=0,
    ),
    FieldDefinition(
        key="shipping_cost", label="Shipping Charges", section=SECTION_PRICING,
        data_type=DataType.NUMBER, collection_type=CollectionType.USER_INPUT,
        required=True, source_hint="User", unit="currency", min_value=0,
    ),
    FieldDefinition(
        key="packaging_cost", label="Packaging Cost", section=SECTION_PRICING,
        data_type=DataType.NUMBER, collection_type=CollectionType.USER_INPUT,
        required=True, source_hint="User", unit="currency", min_value=0,
    ),
    FieldDefinition(
        key="ad_cost", label="Ads Cost", section=SECTION_PRICING,
        data_type=DataType.NUMBER, collection_type=CollectionType.USER_INPUT,
        required=False, source_hint="User", unit="currency", min_value=0,
    ),
    FieldDefinition(
        key="net_cost", label="Net Cost", section=SECTION_PRICING,
        data_type=DataType.NUMBER, collection_type=CollectionType.CALCULATED,
        source_hint="Deterministic", unit="currency",
    ),
    FieldDefinition(
        key="expected_profit", label="Expected Profit", section=SECTION_PRICING,
        data_type=DataType.NUMBER, collection_type=CollectionType.CALCULATED,
        source_hint="Deterministic", unit="currency",
    ),
    FieldDefinition(
        key="margin_pct", label="Margin", section=SECTION_PRICING,
        data_type=DataType.NUMBER, collection_type=CollectionType.CALCULATED,
        source_hint="Deterministic", unit="percent",
    ),
    FieldDefinition(
        key="roi_pct", label="ROI", section=SECTION_PRICING,
        data_type=DataType.NUMBER, collection_type=CollectionType.CALCULATED,
        source_hint="Deterministic", unit="percent",
    ),
    FieldDefinition(
        key="breakeven_units", label="Break Even", section=SECTION_PRICING,
        data_type=DataType.NUMBER, collection_type=CollectionType.CALCULATED,
        source_hint="Deterministic", unit="units",
    ),
    # --- Section 3: Physical Attributes ------------------------------------------
    FieldDefinition(
        key="weight_grams", label="Weight", section=SECTION_PHYSICAL,
        data_type=DataType.NUMBER, collection_type=CollectionType.AUTO_DETECT,
        required=True, source_hint="Marketplace", unit="grams", min_value=0,
    ),
    FieldDefinition(
        key="length_cm", label="Length", section=SECTION_PHYSICAL,
        data_type=DataType.NUMBER, collection_type=CollectionType.AUTO_DETECT,
        required=False, source_hint="Marketplace", unit="cm", min_value=0,
    ),
    FieldDefinition(
        key="width_cm", label="Width", section=SECTION_PHYSICAL,
        data_type=DataType.NUMBER, collection_type=CollectionType.AUTO_DETECT,
        required=False, source_hint="Marketplace", unit="cm", min_value=0,
    ),
    FieldDefinition(
        key="height_cm", label="Height", section=SECTION_PHYSICAL,
        data_type=DataType.NUMBER, collection_type=CollectionType.AUTO_DETECT,
        required=False, source_hint="Marketplace", unit="cm", min_value=0,
    ),
    FieldDefinition(
        key="material", label="Material", section=SECTION_PHYSICAL,
        data_type=DataType.TEXT, collection_type=CollectionType.AUTO_DETECT,
        required=False, source_hint="Marketplace specifications",
        help_text="Auto-detected only if a connector supplies spec-sheet data; otherwise enter manually — Fragility depends on this.",
    ),
    FieldDefinition(
        key="color", label="Color", section=SECTION_PHYSICAL,
        data_type=DataType.TEXT, collection_type=CollectionType.AUTO_DETECT,
        required=False, source_hint="Marketplace",
    ),
    FieldDefinition(
        key="fragility", label="Fragility", section=SECTION_PHYSICAL,
        data_type=DataType.ENUM, collection_type=CollectionType.CALCULATED,
        source_hint="Deterministic", enum_options=["Low", "Medium", "High", "Unknown"],
        help_text="Never asked from the user — inferred from Material via a fixed lookup table.",
    ),
    FieldDefinition(
        key="packaging_type", label="Packaging Type", section=SECTION_PHYSICAL,
        data_type=DataType.TEXT, collection_type=CollectionType.CALCULATED,
        source_hint="Deterministic",
        help_text="Suggested packaging derived from Weight Class + Fragility.",
    ),
    FieldDefinition(
        key="shelf_life_days", label="Shelf Life", section=SECTION_PHYSICAL,
        data_type=DataType.NUMBER, collection_type=CollectionType.USER_INPUT,
        required=False, source_hint="User", unit="days", min_value=0,
    ),
    FieldDefinition(
        key="country_of_origin", label="Country of Origin", section=SECTION_PHYSICAL,
        data_type=DataType.TEXT, collection_type=CollectionType.USER_INPUT,
        required=False, requires_manual_verification=True, source_hint="User",
    ),
    # --- Section 4: Market Information -------------------------------------------
    FieldDefinition(
        key="competition_notes", label="Competition Notes", section=SECTION_MARKET,
        data_type=DataType.LONG_TEXT, collection_type=CollectionType.USER_INPUT,
        required=False, source_hint="User",
    ),
    FieldDefinition(
        key="competitor_count", label="Competitor Count", section=SECTION_MARKET,
        data_type=DataType.NUMBER, collection_type=CollectionType.AUTO_DETECT,
        required=False, source_hint="Marketplace", unit="count", min_value=0,
    ),
    FieldDefinition(
        key="review_count", label="Review Count", section=SECTION_MARKET,
        data_type=DataType.NUMBER, collection_type=CollectionType.AUTO_DETECT,
        required=False, source_hint="Marketplace", unit="count", min_value=0,
    ),
    FieldDefinition(
        key="average_rating", label="Average Rating", section=SECTION_MARKET,
        data_type=DataType.NUMBER, collection_type=CollectionType.AUTO_DETECT,
        required=False, source_hint="Marketplace", unit="/5", min_value=0, max_value=5,
    ),
    FieldDefinition(
        key="review_notes", label="Review Notes", section=SECTION_MARKET,
        data_type=DataType.LONG_TEXT, collection_type=CollectionType.USER_INPUT,
        required=False, source_hint="User",
    ),
    FieldDefinition(
        key="demand_notes", label="Demand Notes", section=SECTION_MARKET,
        data_type=DataType.LONG_TEXT, collection_type=CollectionType.USER_INPUT,
        required=False, source_hint="User",
    ),
    FieldDefinition(
        key="trend_notes", label="Trend Notes", section=SECTION_MARKET,
        data_type=DataType.LONG_TEXT, collection_type=CollectionType.USER_INPUT,
        required=False, source_hint="User",
    ),
    FieldDefinition(
        key="seasonality", label="Seasonality", section=SECTION_MARKET,
        data_type=DataType.ENUM, collection_type=CollectionType.USER_INPUT,
        required=False, source_hint="User",
        enum_options=["Year-round", "Seasonal peak", "Festive only", "Unknown"],
    ),
    FieldDefinition(
        key="brand_potential", label="Brand Potential", section=SECTION_MARKET,
        data_type=DataType.ENUM, collection_type=CollectionType.USER_INPUT,
        required=False, source_hint="User", enum_options=["Low", "Medium", "High", "Unknown"],
        help_text="Your own qualitative judgment — not AI-scored in this phase (PRS §11 notes this dimension is evidence-poor even with AI).",
    ),
    # --- Section 5: Supplier -------------------------------------------------------
    FieldDefinition(
        key="supplier_name", label="Supplier Name", section=SECTION_SUPPLIER,
        data_type=DataType.TEXT, collection_type=CollectionType.USER_INPUT,
        required=True, source_hint="User",
    ),
    FieldDefinition(
        key="manufacturer_name", label="Manufacturer", section=SECTION_SUPPLIER,
        data_type=DataType.TEXT, collection_type=CollectionType.USER_INPUT,
        required=False, source_hint="User",
    ),
    FieldDefinition(
        key="is_importer", label="Importer", section=SECTION_SUPPLIER,
        data_type=DataType.BOOLEAN, collection_type=CollectionType.USER_INPUT,
        required=False, source_hint="User",
    ),
    FieldDefinition(
        key="moq", label="MOQ", section=SECTION_SUPPLIER,
        data_type=DataType.NUMBER, collection_type=CollectionType.USER_INPUT,
        required=False, source_hint="Supplier", unit="units", min_value=0,
    ),
    FieldDefinition(
        key="sample_ordered", label="Sample Ordered", section=SECTION_SUPPLIER,
        data_type=DataType.BOOLEAN, collection_type=CollectionType.USER_INPUT,
        required=False, source_hint="User",
    ),
    FieldDefinition(
        key="lead_time_days", label="Lead Time", section=SECTION_SUPPLIER,
        data_type=DataType.NUMBER, collection_type=CollectionType.USER_INPUT,
        required=False, source_hint="Supplier", unit="days", min_value=0,
    ),
    FieldDefinition(
        key="gst_available", label="GST Available", section=SECTION_SUPPLIER,
        data_type=DataType.BOOLEAN, collection_type=CollectionType.USER_INPUT,
        required=False, requires_manual_verification=True, source_hint="Supplier",
    ),
    FieldDefinition(
        key="supplier_notes", label="Supplier Notes", section=SECTION_SUPPLIER,
        data_type=DataType.LONG_TEXT, collection_type=CollectionType.USER_INPUT,
        required=False, source_hint="User",
    ),
    # --- Auto-calculated summary fields (not tied to one section's raw inputs) -----
    FieldDefinition(
        key="weight_class", label="Weight Class", section=SECTION_PHYSICAL,
        data_type=DataType.ENUM, collection_type=CollectionType.CALCULATED,
        source_hint="Deterministic", enum_options=["Light", "Medium", "Heavy", "Unknown"],
    ),
    FieldDefinition(
        key="fragility_score", label="Fragility Score", section=SECTION_PHYSICAL,
        data_type=DataType.NUMBER, collection_type=CollectionType.CALCULATED,
        source_hint="Deterministic", unit="/100",
    ),
    FieldDefinition(
        key="profitability_score", label="Profitability Score", section=SECTION_PRICING,
        data_type=DataType.NUMBER, collection_type=CollectionType.CALCULATED,
        source_hint="Deterministic", unit="/100",
    ),
]

FIELD_REGISTRY: dict[str, FieldDefinition] = {f.key: f for f in _REGISTRY_LIST}

INPUT_FIELD_KEYS: list[str] = [
    f.key for f in _REGISTRY_LIST if f.collection_type != CollectionType.CALCULATED
]
CALCULATED_FIELD_KEYS: list[str] = [
    f.key for f in _REGISTRY_LIST if f.collection_type == CollectionType.CALCULATED
]
REQUIRED_FIELD_KEYS: list[str] = [f.key for f in _REGISTRY_LIST if f.required]

# Fields we can genuinely auto-detect TODAY, without any connector — currently
# only Category (deterministic keyword match, reused from Phase 1). Sub Category
# is tagged AUTO_DETECT for future policy but has no real detector yet (Phase 1's
# classifier doesn't produce one), so it is deliberately NOT included here —
# it falls through to "ask the user" honestly, same as every other AUTO_DETECT
# field with no connector. Everything else tagged AUTO_DETECT in the registry
# above is a future-connector policy, not a present capability — see collector.py.
CURRENTLY_AUTO_DETECTABLE_KEYS: set[str] = {"category"}
