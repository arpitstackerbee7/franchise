# Copyright (c) 2026, and contributors
# For license information, please see license.txt

"""Inter-store Stock Transfer Candidates.

Styles (Item.custom_barcode_code) selling out in some stores while stuck in others,
from the stores' own data up to the As On Date. For each style in each store:
In = accepted qty of its Purchase Receipts, Out = qty of its Delivery Notes (returns
excluded), sell-through = Out / In, balance = the stock it holds.

Hot (needs stock): sell-through 85%+ and nothing left. Qty Sold is what those
stores sold of the style (Delivery Note qty).
Dead (stock stuck): part of what the store received never sold (In - Out > 0),
e.g. 5 received, 3 sold: 2 stuck. Qty Stuck is that never-sold qty.
A style is listed when it is dead in at least one store and hot in another, so the
stuck stock can be moved to the stores selling it out.
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate, today

HOT_MIN_SELL_THROUGH = 85
TOP_DEAD_STORES = 10


def execute(filters=None):
	filters = frappe._dict(filters or {})
	as_on_date = getdate(filters.get("as_on_date") or today())
	message = _(
		"<b>Inter-store Stock Transfer Candidates</b><br>Styles selling out ({0}%+ sell-through, nothing left) in some stores while qty received in others never sold"
	).format(HOT_MIN_SELL_THROUGH)
	return get_columns(), get_data(as_on_date), message


def get_columns():
	return [
		{"label": _("Style"), "fieldname": "style", "fieldtype": "Data", "width": 140},
		{"label": _("Qty Stuck in Dead Stores"), "fieldname": "stuck_qty", "fieldtype": "Int", "width": 170},
		{"label": _("Dead Store Count"), "fieldname": "dead_count", "fieldtype": "Int", "width": 140},
		{"label": _("Top Dead Stores (store qty)"), "fieldname": "dead_stores", "fieldtype": "Data", "width": 420},
		{"label": _("Qty Sold in Hot Stores"), "fieldname": "sold_qty", "fieldtype": "Int", "width": 170},
		{"label": _("Stockout Hot Store Count"), "fieldname": "hot_count", "fieldtype": "Int", "width": 180},
		{"label": _("Hot Stores Needing Stock (store qty sold)"), "fieldname": "hot_stores", "fieldtype": "Data", "width": 420},
	]


def get_distributors():
	"""Companies that dispatch stock to the stores (they sell to internal customers)."""
	return frappe.db.sql_list(
		"""
		select distinct si.company
		from `tabSales Invoice` si
		join `tabCustomer` c on c.name = si.customer
		where si.docstatus = 1 and ifnull(c.is_internal_customer, 0) = 1
		"""
	)


def get_data(as_on_date):
	values = {"as_on_date": as_on_date, "distributors": get_distributors() or [""]}

	# stock held per store and style
	stock = frappe.db.sql(
		"""
		select
			w.company as store,
			i.custom_barcode_code as style,
			sum(sle.actual_qty) as bal_qty
		from `tabStock Ledger Entry` sle
		join `tabWarehouse` w on w.name = sle.warehouse
		join `tabItem` i on i.name = sle.item_code
		where sle.is_cancelled = 0
			and sle.posting_date <= %(as_on_date)s
			and w.company not in %(distributors)s
			and ifnull(i.custom_barcode_code, '') != ''
		group by w.company, i.custom_barcode_code
		""",
		values,
		as_dict=True,
	)

	# In: accepted qty on Purchase Receipts; Out: qty on Delivery Notes
	in_qty = qty_by_store_style(
		"""
		select pr.company, i.custom_barcode_code, sum(pri.qty)
		from `tabPurchase Receipt Item` pri
		join `tabPurchase Receipt` pr on pr.name = pri.parent
		join `tabItem` i on i.name = pri.item_code
		where pr.docstatus = 1 and ifnull(pr.is_return, 0) = 0
			and pr.posting_date <= %(as_on_date)s
			and pr.company not in %(distributors)s
		group by pr.company, i.custom_barcode_code
		""",
		values,
	)
	out_qty = qty_by_store_style(
		"""
		select dn.company, i.custom_barcode_code, sum(dni.qty)
		from `tabDelivery Note Item` dni
		join `tabDelivery Note` dn on dn.name = dni.parent
		join `tabItem` i on i.name = dni.item_code
		where dn.docstatus = 1 and ifnull(dn.is_return, 0) = 0
			and dn.posting_date <= %(as_on_date)s
			and dn.company not in %(distributors)s
		group by dn.company, i.custom_barcode_code
		""",
		values,
	)

	styles = {}
	for row in stock:
		key = (row.store, row.style)
		received = in_qty.get(key, 0)
		if not received:
			continue
		sold = out_qty.get(key, 0)
		sell_through = sold / received * 100
		bal_qty = flt(row.bal_qty)
		style = styles.setdefault(row.style, {"dead": [], "hot": []})

		if sell_through >= HOT_MIN_SELL_THROUGH and bal_qty <= 0:
			style["hot"].append((row.store, sold))
		elif received - sold > 0:
			# stuck: received in the store but never sold
			style["dead"].append((row.store, received - sold))

	data = []
	for style, s in styles.items():
		if not (s["dead"] and s["hot"]):
			continue
		dead = sorted(s["dead"], key=lambda d: (-d[1], d[0]))
		hot = sorted(s["hot"], key=lambda d: (-d[1], d[0]))
		data.append(
			{
				"style": style,
				"stuck_qty": sum(qty for _store, qty in dead),
				"dead_count": len(dead),
				"dead_stores": ", ".join(f"{store} ({qty:g})" for store, qty in dead[:TOP_DEAD_STORES]),
				"sold_qty": sum(sold for _store, sold in hot),
				"hot_count": len(hot),
				"hot_stores": ", ".join(f"{store} ({sold:g})" for store, sold in hot),
			}
		)

	# most stuck stock first
	data.sort(key=lambda d: (-d["stuck_qty"], -d["hot_count"], d["style"]))
	return data


def qty_by_store_style(query, values):
	return {(store, style): flt(qty) for store, style, qty in frappe.db.sql(query, values)}
