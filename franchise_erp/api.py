import frappe

def round_to_nearest_9(rate):
    """
    Rule:
    - Agar last digit 9 hai → no change
    - Agar last digit <= 5 → pichla 9
    - Agar last digit > 5 → agla 9
    """

    if not rate:
        return rate

    rate = int(round(rate))
    last_digit = rate % 10

    # Already 9 hai, kuch change nahi
    if last_digit == 9:
        return rate

    # 5 ya kam → pichla 9
    if last_digit <= 5:
        return rate - last_digit - 1

    # 5 se zyada → agla 9
    return rate + (9 - last_digit)


def apply_rounding_on_doc(doc):
    """
    Ye function Sales documents ke items par rounding apply karega
    """
    for item in doc.items:
        old_rate = item.rate
        new_rate = round_to_nearest_9(item.rate)
        item.rate = new_rate

        frappe.logger().info(
            f"Pricing Round Utility | {item.item_code} : {old_rate} -> {new_rate}"
        )










def on_change(doc, method):


    apply_rounding_on_doc(doc)
