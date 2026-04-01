import frappe

def short_fy_naming(doc, method=None):
    try:
        if not doc.name:
            return

        # Only run when FY present
        if "202" not in doc.name:
            return

        name = doc.name
        parts = name.split("-")

        for i in range(len(parts)-1):
            if len(parts[i]) == 4 and parts[i].isdigit():
                if len(parts[i+1]) == 4 and parts[i+1].isdigit():

                    short_fy = parts[i][-2:] + "-" + parts[i+1][-2:]
                    full_fy = parts[i] + "-" + parts[i+1]

                    doc.name = name.replace(full_fy, short_fy)
                    break

    except Exception:
        frappe.log_error(frappe.get_traceback(), "FY Short Naming Error")