# import frappe

# def short_fy_naming(doc, method=None):
#     try:
#         if not doc.name:
#             return

#         # Only run when FY present
#         if "202" not in doc.name:
#             return

#         name = doc.name
#         parts = name.split("-")

#         for i in range(len(parts)-1):
#             if len(parts[i]) == 4 and parts[i].isdigit():
#                 if len(parts[i+1]) == 4 and parts[i+1].isdigit():

#                     short_fy = parts[i][-2:] + "-" + parts[i+1][-2:]
#                     full_fy = parts[i] + "-" + parts[i+1]

#                     doc.name = name.replace(full_fy, short_fy)
#                     break

#     except Exception:
#         frappe.log_error(frappe.get_traceback(), "FY Short Naming Error")


import frappe

def short_fy_naming(doc, method=None):
    try:
        if not doc.name:
            return

        name = doc.name

        # Split by both possible separators
        separators = ["-", "/"]

        for sep in separators:
            parts = name.split(sep)

            for part in parts:
                # Check pattern like 2026-2027 manually
                if len(part) == 9 and "-" in part:
                    years = part.split("-")

                    if (
                        len(years) == 2
                        and years[0].isdigit()
                        and years[1].isdigit()
                        and len(years[0]) == 4
                        and len(years[1]) == 4
                    ):
                        short_fy = years[0][-2:] + "-" + years[1][-2:]
                        doc.name = name.replace(part, short_fy)
                        return

    except Exception:
        frappe.log_error(frappe.get_traceback(), "FY Short Naming Error")
