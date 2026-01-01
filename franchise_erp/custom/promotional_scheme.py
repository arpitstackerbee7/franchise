import frappe
from frappe.utils import today, flt

# ============================================================
# MAIN ENTRY
# ============================================================

def apply_promotions(doc, method=None):
    if doc.ignore_pricing_rule:
        return

    # Prevent double execution in same save
    if getattr(doc, "_promotion_applied", False):
        return
    doc._promotion_applied = True

    # Reset everything first
    reset_previous_promotions(doc)

    scheme = get_active_scheme(doc)
    if not scheme:
        return

    slab = get_applicable_slab(scheme)
    if not slab:
        return

    eligible_items = get_eligible_items(doc, scheme)
    if not eligible_items:
        return

    total_qty = sum(int(row.qty) for row in eligible_items)

    # --------------------------------------------------------
    # BUY N GET X FREE
    # --------------------------------------------------------
    if slab.custom_get_1_free:
        n = int(slab.custom_enter_1 or 0)
        x = int(slab.custom_free_item_no or 0)

        if n > 0 and x > 0 and total_qty >= (n + x):
            apply_buy_n_get_x_free(doc, eligible_items, n, x)

    # --------------------------------------------------------
    # BUY N GET X% OFF
    # --------------------------------------------------------
    elif slab.custom_get_50_off:
        n = int(slab.custom_enter_50 or 0)
        percent = flt(slab.custom_enter_percent or 0)

        if n > 0 and percent > 0 and total_qty >= n:
            apply_buy_n_get_x_percent_off(doc, eligible_items, n, percent)

    # --------------------------------------------------------
    # FINAL RECALC
    # --------------------------------------------------------
    recalc_totals(doc)


# ============================================================
# RESET PREVIOUS PROMOTIONS (CRITICAL)
# ============================================================

def reset_previous_promotions(doc):
    # Remove promotion-created rows
    doc.items = [row for row in doc.items if not getattr(row, "is_free_item", 0)]

    for row in doc.items:
        # Always restore rate from price_list_rate
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


def get_applicable_slab(scheme):
    return scheme.price_discount_slabs[0] if scheme.price_discount_slabs else None


# ============================================================
# ELIGIBLE ITEM FILTERING
# ============================================================

def get_eligible_items(doc, scheme):
    items = []

    for row in doc.items:
        if getattr(row, "is_free_item", 0):
            continue

        if scheme.apply_rule_on_other == "Item Group":
            if scheme.other_item_group != "All Item Groups":
                if row.item_group != scheme.other_item_group:
                    continue

        if row.qty > 0 and row.price_list_rate > 0:
            items.append(row)

    return items


# ============================================================
# PROMOTION LOGIC
# ============================================================

def apply_buy_n_get_x_free(doc, items, n, x):
    """
    Buy N Get X Free
    Free items selected using LOWEST price_list_rate
    """

    total_qty = sum(int(r.qty) for r in items)
    eligible_sets = total_qty // (n + x)
    free_units = eligible_sets * x

    if free_units <= 0:
        return

    # Sort by ORIGINAL price (price_list_rate)
    items.sort(key=lambda r: r.price_list_rate)

    for row in items:
        if free_units <= 0:
            break

        if row.qty <= free_units:
            row.discount_percentage = 100
            row.discount_amount = flt(row.price_list_rate * row.qty)
            row.is_free_item = 1
            free_units -= row.qty
        else:
            # Split free units
            free_row = doc.append("items", {})
            copy_item_fields(row, free_row)

            free_row.qty = free_units
            free_row.rate = row.price_list_rate
            free_row.price_list_rate = row.price_list_rate
            free_row.discount_percentage = 100
            free_row.discount_amount = flt(row.price_list_rate * free_units)
            free_row.is_free_item = 1

            row.qty -= free_units
            free_units = 0


def apply_buy_n_get_x_percent_off(doc, items, n, percent):
    """
    Buy N Get X% Off
    Discount applied on ONE lowest price_list_rate unit
    """

    if sum(int(r.qty) for r in items) < n:
        return

    # Sort by price_list_rate
    items.sort(key=lambda r: r.price_list_rate)
    row = items[0]

    discounted_rate = flt(row.price_list_rate * (100 - percent) / 100)

    if int(row.qty) == 1:
        row.rate = discounted_rate
    else:
        discount_row = doc.append("items", {})
        copy_item_fields(row, discount_row)

        discount_row.qty = 1
        discount_row.rate = discounted_rate
        discount_row.price_list_rate = row.price_list_rate

        row.qty -= 1


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
    fields = [
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

    for f in fields:
        if hasattr(source, f):
            setattr(target, f, getattr(source, f))
