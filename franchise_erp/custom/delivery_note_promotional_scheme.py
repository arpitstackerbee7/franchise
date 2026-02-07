import frappe
from frappe.utils import today, flt

# ============================================================
# MAIN ENTRY
# ============================================================
# def get_all_active_schemes(doc):
#     schemes = frappe.get_all(
#         "Promotional Scheme",
#         filters={
#             "selling": 1,
#             "disable": 0,
#             "apply_on": "Transaction",
#             "company": doc.company,
#             "valid_from": ["<=", today()],
#             "valid_upto": [">=", today()]
#         },
#         fields=["name"],
#         order_by="creation asc"
#     )

#     applicable_schemes = []
#     for s in schemes:
#         scheme = frappe.get_doc("Promotional Scheme", s.name)
#         if is_scheme_applicable(scheme, doc):
#             applicable_schemes.append(scheme)

#     return applicable_schemes
def get_all_active_schemes(doc):
    schemes = frappe.get_all(
        "Promotional Scheme",
        filters={
            "selling": 1,
            "disable": 0,
            "company": doc.company,
            "valid_from": ["<=", today()],
            "valid_upto": [">=", today()]
        },
        fields=["name", "apply_on"],
        order_by="creation asc"
    )

    applicable_schemes = []
    for s in schemes:
        scheme = frappe.get_doc("Promotional Scheme", s.name)
        if is_scheme_applicable(scheme, doc):
            applicable_schemes.append(scheme)

    return applicable_schemes

def apply_promotions(doc, method=None):
    if doc.docstatus == 1 or doc.ignore_pricing_rule:
        return

    if getattr(doc, "_promotion_applied", False):
        return
    doc._promotion_applied = True

    reset_previous_promotions(doc)

    schemes = get_all_active_schemes(doc)
    if not schemes:
        return

    for scheme in schemes:
        eligible_items = get_eligible_items(doc, scheme)
        if not eligible_items:
            continue

        total_qty = sum(flt(i.qty) for i in eligible_items)
        slab = get_applicable_slab(scheme, total_qty)
        if not slab:
            continue

        if slab.custom_get_1_free:
            apply_buy_n_get_x_free(
                doc,
                eligible_items,
                int(slab.custom_enter_1),
                int(slab.custom_free_item_no)
            )

        if slab.custom_get_50_off:
            apply_buy_n_get_x_percent_off(
                doc,
                eligible_items,
                int(slab.custom_enter_50),
                flt(slab.custom_enter_percent)
            )

    # 🔥 CRITICAL
    reset_tax_calculation_fields(doc)

    # 🔥 FORCE ERPNext recalculation
    doc.calculate_taxes_and_totals()


def reset_tax_calculation_fields(doc):
    for row in doc.items:
        row.item_tax_rate = None
        row.item_wise_tax_detail = None
        row.base_rate = 0
        row.base_amount = 0
        row.net_rate = 0
        row.net_amount = 0

def get_applicable_slab(scheme, total_qty):
    """
    Returns the highest applicable slab based on total_qty
    """
    if not getattr(scheme, "price_discount_slabs", None):
        return None

    # Highest priority slab first
    slabs = sorted(
        scheme.price_discount_slabs,
        key=lambda x: flt(getattr(x, "min_qty", 0)),
        reverse=True
    )

    for slab in slabs:
        min_qty = flt(getattr(slab, "min_qty", 0))
        max_qty = flt(getattr(slab, "max_qty", 1e9))

        if min_qty <= total_qty <= max_qty:
            return slab

    return None

# ============================================================
# RESET PREVIOUS PROMOTIONS (CRITICAL)
# ============================================================

# def reset_previous_promotions(doc):
#     if doc.docstatus == 1:
#         return
#     # Remove promotion-created rows
#     doc.items = [row for row in doc.items if not getattr(row, "is_free_item", 0)]

#     for row in doc.items:
#         # Always restore rate from price_list_rate
#         if row.price_list_rate:
#             row.rate = row.price_list_rate

#         row.discount_percentage = 0
#         row.discount_amount = 0
#         row.is_free_item = 0

def reset_previous_promotions(doc):
    if doc.docstatus == 1:
        return

    # Remove only free or promo discount rows
    doc.items = [row for row in doc.items if not getattr(row, "is_free_item", 0)]

    for row in doc.items:
        # Agar manual discount hai → skip
        if row.discount_percentage or row.discount_amount:
            continue

        # Promo-applied rows reset
        if getattr(row, "custom_is_promo_scheme", 0):
            if row.price_list_rate:
                row.rate = row.price_list_rate
            row.discount_percentage = 0
            row.discount_amount = 0
            row.is_free_item = 0

# ============================================================
# SCHEME FETCHING
# ============================================================

def get_active_scheme(doc):
    schemes = frappe.get_all(
        "Promotional Scheme",
        filters={
            "selling": 1,
            "disable": 0,
            "apply_on":"Transaction",
            "company": doc.company,
            "valid_from": ["<=", today()],
            "valid_upto": [">=", today()]
        },
        fields=["name"]
    )

    for s in schemes:
        scheme = frappe.get_doc("Promotional Scheme", s.name)
        if is_scheme_applicable(scheme, doc):
            return scheme

    return None


def is_scheme_applicable(scheme, doc):
    if scheme.customer:
        allowed_customers = [c.customer for c in scheme.customer]
        if doc.customer not in allowed_customers:
            return False
    return True


# def get_applicable_slab(scheme):
#     return scheme.price_discount_slabs[0] if scheme.price_discount_slabs else None


# ============================================================
# ELIGIBLE ITEM FILTERING
# ============================================================

# def get_eligible_items(doc, scheme):
#     items = []

#     for row in doc.items:
#         if getattr(row, "is_free_item", 0):
#             continue

#         if scheme.apply_rule_on_other == "Item Group":
#             if scheme.other_item_group != "All Item Groups":
#                 if row.item_group != scheme.other_item_group:
#                     continue

#         if row.qty > 0 and row.price_list_rate > 0:
#             items.append(row)

#     return items

def get_eligible_items(doc, scheme):
    items = []

    apply_on = (scheme.apply_on or "").strip()

    # ---- Pre-calc valid filters (EMPTY = ALL) ----
    valid_item_codes = {d.item_code for d in scheme.items if d.item_code}
    valid_item_groups = {d.item_group for d in scheme.item_groups if d.item_group}
    valid_brands = {d.brand for d in scheme.brands if d.brand}

    for row in doc.items:
        # Skip promo/free rows
        if getattr(row, "is_free_item", 0):
            continue

        if flt(row.qty) <= 0 or flt(row.price_list_rate) <= 0:
            continue

        # 🔹 TRANSACTION → always all
        if apply_on == "Transaction":
            items.append(row)

        # 🔹 ITEM CODE
        elif apply_on == "Item Code":
            if not valid_item_codes or row.item_code in valid_item_codes:
                items.append(row)

        # 🔹 ITEM GROUP
        elif apply_on == "Item Group":
            if not valid_item_groups or row.item_group in valid_item_groups:
                items.append(row)

        # 🔹 BRAND
        elif apply_on == "Brand":
            if not valid_brands or row.brand in valid_brands:
                items.append(row)

    return items

# ============================================================
# PROMOTION LOGIC
# ============================================================

def apply_buy_n_get_x_free(doc, items, n, x):
    total_qty = sum(int(r.qty) for r in items)
    eligible_sets = total_qty // (n + x)
    free_units = eligible_sets * x

    if free_units <= 0:
        return

    items.sort(key=lambda r: r.price_list_rate)  # lowest price first

    for row in items:
        if free_units <= 0:
            break

        if row.qty <= free_units:
            row.discount_percentage = 100
            row.discount_amount = flt(row.price_list_rate * row.qty)
            row.is_free_item = 1
            row.custom_is_promo_scheme = 1
            free_units -= row.qty
        else:
            # Split row for free units
            free_row = doc.append("items", {})
            copy_item_fields(row, free_row)

            free_row.qty = free_units
            free_row.rate = row.price_list_rate
            free_row.price_list_rate = row.price_list_rate
            free_row.discount_percentage = 100
            free_row.discount_amount = flt(row.price_list_rate * free_units)
            free_row.is_free_item = 1
            free_row.custom_is_promo_scheme = 1

            row.qty -= free_units
            free_units = 0



# def apply_buy_n_get_x_percent_off(doc, items, n, percent):
#     """
#     Buy N Get X% Off
#     Discount applied on ONE lowest price_list_rate unit
#     """

#     if sum(int(r.qty) for r in items) < n:
#         return

#     # Sort by price_list_rate
#     items.sort(key=lambda r: r.price_list_rate)
#     row = items[0]

#     discounted_rate = flt(row.price_list_rate * (100 - percent) / 100)

#     if int(row.qty) == 1:
#         row.rate = discounted_rate
#     else:
#         discount_row = doc.append("items", {})
#         copy_item_fields(row, discount_row)

#         discount_row.qty = 1
#         discount_row.rate = discounted_rate
#         discount_row.price_list_rate = row.price_list_rate

#         row.qty -= 1

def apply_buy_n_get_x_percent_off(doc, items, n, percent):
    total_qty = sum(int(r.qty) for r in items)
    if total_qty < n:
        return

    items.sort(key=lambda r: r.price_list_rate)
    discount_sets = total_qty // n
    free_units = discount_sets

    for row in items:
        if free_units <= 0:
            break

        qty_to_discount = min(int(row.qty), free_units)
        discounted_rate = flt(row.price_list_rate * (100 - percent) / 100)

        if qty_to_discount == int(row.qty):
            row.rate = discounted_rate
            row.discount_percentage = percent
            row.custom_is_promo_scheme = 1
            free_units -= qty_to_discount
        else:
            discount_row = doc.append("items", {})
            copy_item_fields(row, discount_row)

            discount_row.qty = qty_to_discount
            discount_row.rate = discounted_rate
            discount_row.price_list_rate = row.price_list_rate
            discount_row.discount_percentage = percent
            discount_row.custom_is_promo_scheme = 1

            row.qty -= qty_to_discount
            free_units -= qty_to_discount

# ============================================================
# TOTAL RECALC
# ============================================================

def recalc_totals(doc):
    for row in doc.items:
        qty = flt(row.qty or 0)

        rate = flt(row.rate or 0)
        base_rate = flt(row.base_rate or row.rate or 0)

        discount = flt(row.discount_amount or 0)

        row.amount = flt((rate * qty) - discount)
        row.base_amount = flt((base_rate * qty) - discount)

    doc.calculate_taxes_and_totals()
# ============================================================
# UTIL
# ============================================================

def copy_item_fields(source, target):
    safe_fields = [
        "item_code",
        "item_name",
        "description",
        "uom",
        "stock_uom",
        "conversion_factor",
        "item_group",
        "warehouse",
        "income_account",
        "cost_center"
    ]

    for f in safe_fields:
        if hasattr(source, f):
            setattr(target, f, getattr(source, f))

    # 🔥 GST & CALCULATION RESET
    target.item_tax_rate = None
    target.item_wise_tax_detail = None
    target.discount_amount = 0
    target.base_rate = 0
    target.base_amount = 0
    target.net_rate = 0
    target.net_amount = 0




def reset_item_tax_details(doc):
    """
    VERY IMPORTANT:
    Clear item-wise tax after rate/qty manipulation
    """
    for item in doc.items:
        item.item_tax_rate = None
        item.item_wise_tax_detail = None
