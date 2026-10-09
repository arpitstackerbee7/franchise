# Copyright (c) 2026, and contributors
# For license information, please see license.txt

"""Chronic Hot vs Dead Stores.

For every store (company), up to the As On Date:
In Qty = accepted qty of its Purchase Receipts, Out Qty = qty of its Delivery Notes
(returns excluded), Bal Value = Total of those Purchase Receipts, Out Value = Total
of those Delivery Notes, Bal Qty = the stock it holds, the styles
(Item.custom_barcode_code) it handled, sell-through = Out / In x 100, and Avg Aging =
the remaining qty's (Purchase Receipt qty - Delivery Note qty, per item) average age
in days since each item's latest Purchase Receipt, weighted by that remaining qty.

Hot stores sell through 80%+ (starving for stock: replenish first);
dead stores sell through under 30% (stock is not moving: investigate execution).
The distributor that dispatches to the stores (sells to internal customers) is left out.
"""

import frappe
from frappe import _
from frappe.utils import date_diff, flt, getdate, today

HOT_MIN_SELL_THROUGH = 80
DEAD_MAX_SELL_THROUGH = 30


def execute(filters=None):
	filters = frappe._dict(filters or {})
	store_type = filters.get("store_type") or "Hot Store"
	as_on_date = getdate(filters.get("as_on_date") or today())

	data = get_data(store_type, as_on_date)
	return get_columns(), data, get_message(store_type)


def get_columns():
	return [
		{"label": _("Store Name"), "fieldname": "store", "fieldtype": "Link", "options": "Company", "width": 240},
		{"label": _("In Qty"), "fieldname": "in_qty", "fieldtype": "Int", "width": 100},
		{"label": _("Out Qty"), "fieldname": "out_qty", "fieldtype": "Int", "width": 100},
		{"label": _("Bal Qty"), "fieldname": "bal_qty", "fieldtype": "Int", "width": 100},
		{"label": _("Bal Value"), "fieldname": "bal_value", "fieldtype": "Currency", "width": 140},
		{"label": _("Out Value"), "fieldname": "out_value", "fieldtype": "Currency", "width": 140},
		{"label": _("Styles"), "fieldname": "styles", "fieldtype": "Int", "width": 90},
		{"label": _("SellThru Pct"), "fieldname": "sell_through", "fieldtype": "Percent", "precision": 1, "width": 110},
		{"label": _("Avg Aging of Balance"), "fieldname": "avg_aging", "fieldtype": "Int", "width": 160},
	]


def get_message(store_type):
	if store_type == "Dead Store":
		return _(
			"<b>Chronic DEAD Stores (sell-through under 30%)</b><br>Same styles as top sellers elsewhere are not moving here — investigate execution, don't just resupply"
		)
	return _("<b>Chronic HOT Stores (sell-through 80%+)</b><br>These stores are starving for stock across styles — replenish first")


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


def get_data(store_type, as_on_date):
	values = {"as_on_date": as_on_date, "distributors": get_distributors() or [""]}

	# stock held and the styles handled, from the store's warehouses
	stores = frappe.db.sql(
		"""
		select
			w.company as store,
			sum(sle.actual_qty) as bal_qty,
			count(distinct nullif(i.custom_barcode_code, '')) as styles
		from `tabStock Ledger Entry` sle
		join `tabWarehouse` w on w.name = sle.warehouse
		join `tabItem` i on i.name = sle.item_code
		where sle.is_cancelled = 0
			and sle.posting_date <= %(as_on_date)s
			and w.company not in %(distributors)s
		group by w.company
		""",
		values,
		as_dict=True,
	)

	# In: accepted qty received on Purchase Receipts; Out: qty sent on Delivery Notes
	in_qty = dict(
		frappe.db.sql(
			"""
			select pr.company, sum(pri.qty)
			from `tabPurchase Receipt Item` pri
			join `tabPurchase Receipt` pr on pr.name = pri.parent
			where pr.docstatus = 1 and ifnull(pr.is_return, 0) = 0
				and pr.posting_date <= %(as_on_date)s
				and pr.company not in %(distributors)s
			group by pr.company
			""",
			values,
		)
	)
	out_qty = dict(
		frappe.db.sql(
			"""
			select dn.company, sum(dni.qty)
			from `tabDelivery Note Item` dni
			join `tabDelivery Note` dn on dn.name = dni.parent
			where dn.docstatus = 1 and ifnull(dn.is_return, 0) = 0
				and dn.posting_date <= %(as_on_date)s
				and dn.company not in %(distributors)s
			group by dn.company
			""",
			values,
		)
	)

	# Bal Value: Total of the Purchase Receipts; Out Value: Total of the Delivery Notes
	bal_value = dict(
		frappe.db.sql(
			"""
			select company, sum(total)
			from `tabPurchase Receipt`
			where docstatus = 1 and ifnull(is_return, 0) = 0
				and posting_date <= %(as_on_date)s
				and company not in %(distributors)s
			group by company
			""",
			values,
		)
	)
	out_value = dict(
		frappe.db.sql(
			"""
			select company, sum(total)
			from `tabDelivery Note`
			where docstatus = 1 and ifnull(is_return, 0) = 0
				and posting_date <= %(as_on_date)s
				and company not in %(distributors)s
			group by company
			""",
			values,
		)
	)

	aging = get_balance_aging(values)

	data = []
	for row in stores:
		row.in_qty = flt(in_qty.get(row.store))
		row.out_qty = flt(out_qty.get(row.store))
		row.bal_value = flt(bal_value.get(row.store))
		row.out_value = flt(out_value.get(row.store))
		if not row.in_qty:
			continue
		row.sell_through = flt(row.out_qty / row.in_qty * 100, 1)
		row.avg_aging = aging.get(row.store, 0)
		if store_type == "Dead Store":
			if row.sell_through < DEAD_MAX_SELL_THROUGH:
				data.append(row)
		elif row.sell_through >= HOT_MIN_SELL_THROUGH:
			data.append(row)

	# hot: best sellers first; dead: the stores where nothing moves first
	if store_type == "Dead Store":
		data.sort(key=lambda r: (r.sell_through, -flt(r.bal_value)))
	else:
		data.sort(key=lambda r: (-r.sell_through, -flt(r.out_value)))
	return data


def get_balance_aging(values):
	"""Per store, the remaining qty's weighted average age:
	for each item, Remaining Qty = Purchase Receipt qty - Delivery Note qty and
	Age Days = As On Date - its latest Purchase Receipt date;
	Avg Aging = sum(Remaining Qty * Age Days) / sum(Remaining Qty)."""
	received = frappe.db.sql(
		"""
		select pr.company as store, pri.item_code, sum(pri.qty) as in_qty, max(pr.posting_date) as last_pr_date
		from `tabPurchase Receipt Item` pri
		join `tabPurchase Receipt` pr on pr.name = pri.parent
		where pr.docstatus = 1 and ifnull(pr.is_return, 0) = 0
			and pr.posting_date <= %(as_on_date)s
			and pr.company not in %(distributors)s
		group by pr.company, pri.item_code
		""",
		values,
		as_dict=True,
	)
	sold = {
		(store, item_code): flt(qty)
		for store, item_code, qty in frappe.db.sql(
			"""
			select dn.company, dni.item_code, sum(dni.qty)
			from `tabDelivery Note Item` dni
			join `tabDelivery Note` dn on dn.name = dni.parent
			where dn.docstatus = 1 and ifnull(dn.is_return, 0) = 0
				and dn.posting_date <= %(as_on_date)s
				and dn.company not in %(distributors)s
			group by dn.company, dni.item_code
			""",
			values,
		)
	}

	totals = {}
	for d in received:
		remaining = flt(d.in_qty) - sold.get((d.store, d.item_code), 0)
		if remaining <= 0:
			continue
		age_days = date_diff(values["as_on_date"], d.last_pr_date)
		t = totals.setdefault(d.store, [0, 0])
		t[0] += remaining * age_days
		t[1] += remaining
	return {store: round(weighted / qty) for store, (weighted, qty) in totals.items() if qty}
