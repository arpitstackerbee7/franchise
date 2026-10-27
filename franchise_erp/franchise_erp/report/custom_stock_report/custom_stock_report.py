# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from operator import itemgetter
from typing import Any, TypedDict

import frappe
from frappe import _
from frappe.query_builder import Order
from frappe.query_builder.functions import Coalesce, Count
from frappe.utils import add_days, cint, date_diff, flt, getdate
from frappe.utils.nestedset import get_descendants_of

import erpnext
from erpnext.stock.doctype.inventory_dimension.inventory_dimension import get_inventory_dimensions
from erpnext.stock.doctype.warehouse.warehouse import apply_warehouse_filter
from erpnext.stock.report.stock_ageing.stock_ageing import FIFOSlots, get_average_age
from erpnext.stock.utils import add_additional_uom_columns

OPENING_SUPPLIER = "TZU Lifestyle Pvt Ltd"


class StockBalanceFilter(TypedDict):
	company: str | None
	from_date: str
	to_date: str
	item_group: str | None
	item: list[str] | None
	warehouse: list[str] | None
	warehouse_type: str | None
	include_uom: str | None  # include extra info in converted UOM
	show_stock_ageing_data: bool
	show_variant_attributes: bool
	closing_balance_name: str | None


SLEntry = dict[str, Any]


def execute(filters: StockBalanceFilter | None = None):
	return StockBalanceReport(filters).run()


class StockBalanceReport:
	def __init__(self, filters: StockBalanceFilter | None) -> None:
		self.filters = frappe._dict(filters or {})

		self.from_date = getdate(self.filters.get("from_date"))
		self.to_date = getdate(self.filters.get("to_date"))

		self.start_from = None
		self.data = []
		self.columns = []
		self.sle_entries: list[SLEntry] = []
		self.closing_balance_name = None

		self.set_company_currency()

	def set_company_currency(self) -> None:
		if self.filters.get("company"):
			self.company_currency = erpnext.get_company_currency(self.filters.get("company"))
		else:
			self.company_currency = frappe.db.get_single_value("Global Defaults", "default_currency")

	def run(self):
		self.float_precision = cint(frappe.db.get_default("float_precision")) or 3

		self.inventory_dimensions = self.get_inventory_dimension_fields()
		self.prepare_opening_data_from_closing_balance()
		self.prepare_stock_ledger_entries()
		self.prepare_new_data()

		self.set_serial_numbers()
		self.set_price_list_rates()
		self.set_supplier_name()

		if not self.columns:
			self.columns = self.get_columns()

		self.add_additional_uom_columns()

		message = {"closing_balance_name": self.closing_balance_name}

		return self.columns, self.data, message

	def prepare_opening_data_from_closing_balance(self) -> None:
		self.opening_data = frappe._dict({})

		closing_balance = self.get_closing_balance()
		if not closing_balance:
			return
		self.closing_balance_name = closing_balance[0].name

		self.start_from = add_days(closing_balance[0].to_date, 1)
		res = frappe.get_doc("Closing Stock Balance", closing_balance[0].name).get_prepared_data()

		for entry in res.data:
			entry = frappe._dict(entry)

			group_by_key = self.get_group_by_key(entry)
			if group_by_key not in self.opening_data:
				self.opening_data.setdefault(group_by_key, entry)

	def prepare_new_data(self):
		self.item_warehouse_map = self.get_item_warehouse_map()

		if self.filters.get("show_stock_ageing_data"):
			self.filters["show_warehouse_wise_stock"] = True
			item_wise_fifo_queue = FIFOSlots(self.filters, self.sle_entries).generate()

		_func = itemgetter(1)

		del self.sle_entries

		sre_details = self.get_sre_reserved_qty_details()

		variant_values = {}
		if self.filters.get("show_variant_attributes"):
			variant_values = self.get_variant_values_for()

		for _key, report_data in self.item_warehouse_map.items():
			if variant_data := variant_values.get(report_data.item_code):
				report_data.update(variant_data)

			if self.filters.get("show_stock_ageing_data"):
				opening_fifo_queue = self.get_opening_fifo_queue(report_data) or []

				fifo_queue = []
				if fifo_queue := item_wise_fifo_queue.get((report_data.item_code, report_data.warehouse)):
					fifo_queue = fifo_queue.get("fifo_queue")

				if fifo_queue:
					opening_fifo_queue.extend(fifo_queue)

				stock_ageing_data = {"average_age": 0, "earliest_age": 0, "latest_age": 0}
				if opening_fifo_queue:
					fifo_queue = sorted(filter(_func, opening_fifo_queue), key=_func)
					if not fifo_queue:
						continue

					to_date = self.to_date
					stock_ageing_data["average_age"] = get_average_age(fifo_queue, to_date)
					stock_ageing_data["earliest_age"] = date_diff(to_date, fifo_queue[0][1])
					stock_ageing_data["latest_age"] = date_diff(to_date, fifo_queue[-1][1])
					stock_ageing_data["fifo_queue"] = fifo_queue

				report_data.update(stock_ageing_data)

			report_data.update(
				{"reserved_stock": sre_details.get((report_data.item_code, report_data.warehouse), 0.0)}
			)

			if (
				not self.filters.get("include_zero_stock_items")
				and report_data
				and report_data.bal_qty == 0
				and report_data.bal_val == 0
			):
				continue

			self.data.append(report_data)

	def get_item_warehouse_map(self):
		item_warehouse_map = {}
		self.opening_vouchers = self.get_opening_vouchers()

		if self.filters.get("show_stock_ageing_data"):
			self.sle_entries = self.sle_query.run(as_dict=True)

		self.prepare_stock_reco_voucher_wise_count()

		# HACK: This is required to avoid causing db query in flt
		_system_settings = frappe.get_cached_doc("System Settings")
		with frappe.db.unbuffered_cursor():
			if not self.filters.get("show_stock_ageing_data"):
				self.sle_entries = self.sle_query.run(as_dict=True, as_iterator=True)

			for entry in self.sle_entries:
				group_by_key = self.get_group_by_key(entry)
				if group_by_key not in item_warehouse_map:
					self.initialize_data(item_warehouse_map, group_by_key, entry)

				self.prepare_item_warehouse_map(item_warehouse_map, entry, group_by_key)

				if self.opening_data.get(group_by_key):
					del self.opening_data[group_by_key]

		for group_by_key, entry in self.opening_data.items():
			if group_by_key not in item_warehouse_map:
				self.initialize_data(item_warehouse_map, group_by_key, entry)

		item_warehouse_map = filter_items_with_no_transactions(
			item_warehouse_map, self.float_precision, self.inventory_dimensions
		)

		return item_warehouse_map

	def prepare_stock_reco_voucher_wise_count(self):
		self.stock_reco_voucher_wise_count = frappe._dict()

		doctype = frappe.qb.DocType("Stock Ledger Entry")
		item = frappe.qb.DocType("Item")

		query = (
			frappe.qb.from_(doctype)
			.inner_join(item)
			.on(doctype.item_code == item.name)
			.select(doctype.voucher_detail_no, Count(doctype.name).as_("count"))
			.where(
				(doctype.voucher_type == "Stock Reconciliation")
				& (doctype.docstatus < 2)
				& (doctype.is_cancelled == 0)
				& (item.has_serial_no == 1)
			)
			.groupby(doctype.voucher_detail_no)
		)

		if items := self.filters.item_code:
			if isinstance(items, str):
				items = [items]

			query = query.where(item.name.isin(items))

		if self.filters.item_group:
			childrens = []
			childrens.append(self.filters.item_group)
			if item_group_childrens := get_descendants_of(
				"Item Group", self.filters.item_group, ignore_permissions=True
			):
				childrens.extend(item_group_childrens)

			if childrens:
				query = query.where(item.item_group.isin(childrens))

		if warehouses := self.filters.get("warehouse"):
			if isinstance(warehouses, str):
				warehouses = [warehouses]

			childrens = []
			for warehouse in warehouses:
				childrens.append(warehouse)
				if warehouse_childrens := get_descendants_of("Warehouse", warehouse, ignore_permissions=True):
					childrens.extend(warehouse_childrens)

			if childrens:
				query = query.where(doctype.warehouse.isin(childrens))

		data = query.run(as_dict=True)
		if not data:
			return

		for row in data:
			if row.count != 1:
				continue

			sr_item = frappe.db.get_value(
				"Stock Reconciliation Item", row.voucher_detail_no, ["current_qty", "qty"], as_dict=True
			)

			if sr_item.qty and sr_item.current_qty:
				self.stock_reco_voucher_wise_count[row.voucher_detail_no] = sr_item.current_qty

	def get_sre_reserved_qty_details(self) -> dict:
		from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
			get_sre_reserved_qty_for_items_and_warehouses as get_reserved_qty_details,
		)

		item_code_list, warehouse_list = [], []
		for d in self.item_warehouse_map:
			item_code_list.append(d[1])
			warehouse_list.append(d[2])

		return get_reserved_qty_details(item_code_list, warehouse_list)

	def prepare_item_warehouse_map(self, item_warehouse_map, entry, group_by_key):
		qty_dict = item_warehouse_map[group_by_key]
		for field in self.inventory_dimensions:
			qty_dict[field] = entry.get(field)

		if entry.voucher_type == "Stock Reconciliation" and (
			not entry.batch_no or entry.serial_no or entry.serial_and_batch_bundle
		):
			if entry.serial_no and entry.voucher_detail_no in self.stock_reco_voucher_wise_count:
				qty_dict.opening_qty -= self.stock_reco_voucher_wise_count.get(entry.voucher_detail_no, 0)
				qty_dict.bal_qty = 0.0
				qty_diff = flt(entry.actual_qty)
			else:
				qty_diff = flt(entry.qty_after_transaction) - flt(qty_dict.bal_qty)
		else:
			qty_diff = flt(entry.actual_qty)

		value_diff = flt(entry.stock_value_difference)

		if entry.posting_date < self.from_date or entry.voucher_no in self.opening_vouchers.get(
			entry.voucher_type, []
		):
			qty_dict.opening_qty += qty_diff
			qty_dict.opening_val += value_diff

		elif entry.posting_date >= self.from_date and entry.posting_date <= self.to_date:
			if flt(qty_diff, self.float_precision) >= 0:
				qty_dict.in_qty += qty_diff
			else:
				qty_dict.out_qty += abs(qty_diff)

			if flt(value_diff, self.float_precision) >= 0:
				qty_dict.in_val += value_diff
			else:
				qty_dict.out_val += abs(value_diff)

		qty_dict.val_rate = entry.valuation_rate
		qty_dict.bal_qty += qty_diff
		qty_dict.bal_val += value_diff

	def initialize_data(self, item_warehouse_map, group_by_key, entry):
		opening_data = self.opening_data.get(group_by_key, {})

		item_warehouse_map[group_by_key] = frappe._dict(
			{
				"item_code": entry.item_code,
				"warehouse": entry.warehouse,
				"item_group": entry.item_group,
				"company": entry.company,
				"currency": self.company_currency,
				"stock_uom": entry.stock_uom,
				"item_name": entry.item_name,
				"style": entry.custom_barcode_code,
				"top_fabric": entry.custom_top_fabrics,
				"sup_design_no": entry.custom_sup_design_no,
				"image": entry.image,
				"opening_qty": opening_data.get("bal_qty") or 0.0,
				"opening_val": opening_data.get("bal_val") or 0.0,
				"opening_fifo_queue": opening_data.get("fifo_queue") or [],
				"in_qty": 0.0,
				"in_val": 0.0,
				"out_qty": 0.0,
				"out_val": 0.0,
				"bal_qty": opening_data.get("bal_qty") or 0.0,
				"bal_val": opening_data.get("bal_val") or 0.0,
				"val_rate": 0.0,
			}
		)

	def get_group_by_key(self, row) -> tuple:
		group_by_key = [row.company, row.item_code, row.warehouse]

		for fieldname in self.inventory_dimensions:
			if not row.get(fieldname):
				continue

			if self.filters.get(fieldname) or self.filters.get("show_dimension_wise_stock"):
				group_by_key.append(row.get(fieldname))

		return tuple(group_by_key)

	def get_closing_balance(self) -> list[dict[str, Any]]:
		if self.filters.get("ignore_closing_balance"):
			return []

		if self.filters.get("closing_balance_name"):
			return frappe.get_all(
				"Closing Stock Balance",
				filters={"name": self.filters.get("closing_balance_name"), "docstatus": 1},
				fields=["name", "to_date"],
			)
		table = frappe.qb.DocType("Closing Stock Balance")

		query = (
			frappe.qb.from_(table)
			.select(table.name, table.to_date)
			.where(
				(table.docstatus == 1)
				& (table.company == self.filters.company)
				& (table.to_date <= self.from_date)
				& (table.status == "Completed")
			)
			.orderby(table.to_date, order=Order.desc)
			.limit(1)
		)

		for fieldname in ["warehouse", "item_code", "item_group", "warehouse_type"]:
			if value := self.filters.get(fieldname):
				if isinstance(value, list | tuple):
					query = query.where(table[fieldname].isin(value))
				else:
					query = query.where(table[fieldname] == value)

		return query.run(as_dict=True)

	def prepare_stock_ledger_entries(self):
		sle = frappe.qb.DocType("Stock Ledger Entry")
		item_table = frappe.qb.DocType("Item")

		query = (
			frappe.qb.from_(sle)
			.inner_join(item_table)
			.on(sle.item_code == item_table.name)
			.select(
				sle.item_code,
				sle.warehouse,
				sle.posting_date,
				sle.actual_qty,
				sle.valuation_rate,
				sle.company,
				sle.voucher_type,
				sle.qty_after_transaction,
				sle.stock_value_difference,
				sle.item_code.as_("name"),
				sle.voucher_no,
				sle.stock_value,
				sle.batch_no,
				sle.serial_no,
				sle.serial_and_batch_bundle,
				sle.has_serial_no,
				sle.voucher_detail_no,
				item_table.item_group,
				item_table.stock_uom,
				item_table.item_name,
				item_table.custom_barcode_code,
				item_table.custom_top_fabrics,
				item_table.custom_sup_design_no,
				item_table.image,
			)
			.where((sle.docstatus < 2) & (sle.is_cancelled == 0))
			.orderby(sle.posting_datetime)
			.orderby(sle.creation)
		)

		query = self.apply_inventory_dimensions_filters(query, sle)
		query = self.apply_warehouse_filters(query, sle)
		query = self.apply_items_filters(query, item_table)
		query = self.apply_date_filters(query, sle)

		if self.filters.get("company"):
			query = query.where(sle.company == self.filters.get("company"))

		self.sle_query = query

	def apply_inventory_dimensions_filters(self, query, sle) -> str:
		inventory_dimension_fields = self.get_inventory_dimension_fields()
		if inventory_dimension_fields:
			for fieldname in inventory_dimension_fields:
				query = query.select(fieldname)
				if self.filters.get(fieldname):
					query = query.where(sle[fieldname].isin(self.filters.get(fieldname)))

		return query

	def apply_warehouse_filters(self, query, sle) -> str:
		warehouse_table = frappe.qb.DocType("Warehouse")

		if self.filters.get("warehouse"):
			query = apply_warehouse_filter(query, sle, self.filters)

		elif warehouse_type := self.filters.get("warehouse_type"):
			query = (
				query.join(warehouse_table)
				.on(warehouse_table.name == sle.warehouse)
				.where(warehouse_table.warehouse_type == warehouse_type)
			)

		return query

	def apply_items_filters(self, query, item_table) -> str:
		if item_group := self.filters.get("item_group"):
			children = get_descendants_of("Item Group", item_group, ignore_permissions=True)
			query = query.where(item_table.item_group.isin([*children, item_group]))

		if item_codes := self.filters.get("item_code"):
			query = query.where(item_table.name.isin(item_codes))

		if brand := self.filters.get("brand"):
			query = query.where(item_table.brand == brand)

		return query

	def apply_date_filters(self, query, sle) -> str:
		if not self.filters.ignore_closing_balance and self.start_from:
			query = query.where(sle.posting_date >= self.start_from)

		if self.to_date:
			query = query.where(sle.posting_date <= self.to_date)

		return query

	# ------------------------------------------------------------------
	# Serial numbers (single query for all rows)
	# ------------------------------------------------------------------
	def set_serial_numbers(self):
		if not self.data:
			return

		item_codes = list({r.item_code for r in self.data})

		rows = frappe.db.sql(
			"""
			SELECT item_code, warehouse, name
			FROM `tabSerial No`
			WHERE status = 'Active'
				AND item_code IN %(items)s
				AND IFNULL(warehouse, '') != ''
			ORDER BY name
			""",
			{"items": item_codes},
			as_dict=True,
		)

		serial_map = {}
		for d in rows:
			serial_map.setdefault((d.item_code, d.warehouse), []).append(d.name)

		for row in self.data:
			serials = serial_map.get((row.item_code, row.warehouse), [])
			row.serial_no = ", ".join(serials)
			row.serial_count = len(serials)

	def set_price_list_rates(self):
		if not self.data:
			return

		item_codes = list({d.item_code for d in self.data})

		prices = frappe.get_all(
			"Item Price",
			filters={
				"item_code": ["in", item_codes],
				"price_list": ["in", ["STD", "WSP", "MRP"]],
			},
			fields=["item_code", "price_list", "price_list_rate"],
		)

		price_map = {}

		for d in prices:
			price_map.setdefault(d.item_code, {})
			price_map[d.item_code][d.price_list] = d.price_list_rate

		for row in self.data:
			row.std_rate = price_map.get(row.item_code, {}).get("STD", 0)
			row.wsp_rate = price_map.get(row.item_code, {}).get("WSP", 0)
			row.mrp_rate = price_map.get(row.item_code, {}).get("MRP", 0)

	# ------------------------------------------------------------------
	# Party Name / Last Stock In Date / Party City
	# ------------------------------------------------------------------
	def set_supplier_name(self):
		"""
		Party Name priority (every row gets a value):
		1. Opening stock (item + warehouse)                       -> TZU Lifestyle Pvt Ltd
		2. PR / PI / Subcontracting Receipt / Serial No supplier  (item + warehouse)
		3. Same suppliers, item level (any warehouse, latest date)
		4. Everything else (Stock Entry / Sales Return / Delivery
		   Note return / no purchase record at all)               -> TZU Lifestyle Pvt Ltd

		Last Stock In Date: last Stock Ledger IN entry (item + warehouse) <= to_date,
		fallback to the supplier document date.
		"""
		rows = [r for r in self.data if r.item_code]
		if not rows:
			return

		item_codes = list({r.item_code for r in rows})
		params = {"items": item_codes, "to_date": self.to_date}

		# ---------- Opening stock (Stock Reconciliation / Stock Entry) ----------
		opening_rows = frappe.db.sql(
			"""
			SELECT DISTINCT sle.item_code, sle.warehouse
			FROM `tabStock Ledger Entry` sle
			LEFT JOIN `tabStock Reconciliation` sr
				ON sle.voucher_type = 'Stock Reconciliation'
				AND sr.name = sle.voucher_no
				AND sr.docstatus = 1
				AND sr.purpose = 'Opening Stock'
			LEFT JOIN `tabStock Entry` se
				ON sle.voucher_type = 'Stock Entry'
				AND se.name = sle.voucher_no
				AND se.docstatus = 1
				AND se.is_opening = 'Yes'
			WHERE sle.item_code IN %(items)s
				AND sle.is_cancelled = 0
				AND sle.actual_qty > 0
				AND sle.posting_date <= %(to_date)s
				AND (sr.name IS NOT NULL OR se.name IS NOT NULL)
			""",
			params,
			as_dict=True,
		)
		opening_wh_set = {(d.item_code, d.warehouse) for d in opening_rows}

		# ---------- Latest supplier per (item, warehouse) ----------
		pr_data = frappe.db.sql(
			"""
			SELECT item_code, warehouse, supplier, posting_date FROM (
				SELECT pri.item_code, pri.warehouse, pr.supplier, pr.posting_date,
					ROW_NUMBER() OVER (
						PARTITION BY pri.item_code, pri.warehouse
						ORDER BY pr.posting_date DESC, pr.creation DESC
					) AS rn
				FROM `tabPurchase Receipt Item` pri
				INNER JOIN `tabPurchase Receipt` pr ON pr.name = pri.parent
				WHERE pr.docstatus = 1
					AND pr.posting_date <= %(to_date)s
					AND pri.item_code IN %(items)s
			) t WHERE rn = 1
			""",
			params,
			as_dict=True,
		)

		pi_data = frappe.db.sql(
			"""
			SELECT item_code, warehouse, supplier, posting_date FROM (
				SELECT pii.item_code, pii.warehouse, pi.supplier, pi.posting_date,
					ROW_NUMBER() OVER (
						PARTITION BY pii.item_code, pii.warehouse
						ORDER BY pi.posting_date DESC, pi.creation DESC
					) AS rn
				FROM `tabPurchase Invoice Item` pii
				INNER JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
				WHERE pi.docstatus = 1
					AND pi.update_stock = 1
					AND pi.posting_date <= %(to_date)s
					AND pii.item_code IN %(items)s
			) t WHERE rn = 1
			""",
			params,
			as_dict=True,
		)

		scr_data = frappe.db.sql(
			"""
			SELECT item_code, warehouse, supplier, posting_date FROM (
				SELECT scri.item_code, scri.warehouse, scr.supplier, scr.posting_date,
					ROW_NUMBER() OVER (
						PARTITION BY scri.item_code, scri.warehouse
						ORDER BY scr.posting_date DESC, scr.creation DESC
					) AS rn
				FROM `tabSubcontracting Receipt Item` scri
				INNER JOIN `tabSubcontracting Receipt` scr ON scr.name = scri.parent
				WHERE scr.docstatus = 1
					AND scr.posting_date <= %(to_date)s
					AND scri.item_code IN %(items)s
			) t WHERE rn = 1
			""",
			params,
			as_dict=True,
		)

		# Serial No -> purchase_document_no matched by document name
		# (this site's Serial No has no purchase_document_type field)
		serial_data = frappe.db.sql(
			"""
			SELECT item_code, warehouse, supplier, posting_date FROM (
				SELECT
					sn.item_code,
					sn.warehouse,
					COALESCE(pr.supplier, pi.supplier, scr.supplier) AS supplier,
					COALESCE(pr.posting_date, pi.posting_date, scr.posting_date) AS posting_date,
					ROW_NUMBER() OVER (
						PARTITION BY sn.item_code, sn.warehouse
						ORDER BY COALESCE(pr.posting_date, pi.posting_date, scr.posting_date) DESC,
							sn.creation DESC
					) AS rn
				FROM `tabSerial No` sn
				LEFT JOIN `tabPurchase Receipt` pr
					ON pr.name = sn.purchase_document_no AND pr.docstatus = 1
				LEFT JOIN `tabPurchase Invoice` pi
					ON pi.name = sn.purchase_document_no AND pi.docstatus = 1
				LEFT JOIN `tabSubcontracting Receipt` scr
					ON scr.name = sn.purchase_document_no AND scr.docstatus = 1
				WHERE sn.item_code IN %(items)s
					AND IFNULL(sn.warehouse, '') != ''
					AND IFNULL(sn.purchase_document_no, '') != ''
					AND COALESCE(pr.supplier, pi.supplier, scr.supplier) IS NOT NULL
			) t WHERE rn = 1
			""",
			params,
			as_dict=True,
		)

		# ---------- merge by priority ----------
		wh_map = {}    # (item, warehouse) -> info (source priority PR > PI > SCR > Serial)
		item_map = {}  # item -> latest info across all sources (fallback)

		for source in (pr_data, pi_data, scr_data, serial_data):
			for d in source:
				if not d.supplier:
					continue

				info = {"supplier": d.supplier, "date": d.posting_date}

				if d.warehouse:
					wh_map.setdefault((d.item_code, d.warehouse), info)

				existing = item_map.get(d.item_code)
				if not existing or (
					d.posting_date and (not existing["date"] or d.posting_date > existing["date"])
				):
					item_map[d.item_code] = info

		# ---------- last stock in date from Stock Ledger ----------
		sle_data = frappe.db.sql(
			"""
			SELECT item_code, warehouse, MAX(posting_date) AS last_in
			FROM `tabStock Ledger Entry`
			WHERE item_code IN %(items)s
				AND actual_qty > 0
				AND is_cancelled = 0
				AND posting_date <= %(to_date)s
			GROUP BY item_code, warehouse
			""",
			params,
			as_dict=True,
		)
		last_in_map = {(d.item_code, d.warehouse): d.last_in for d in sle_data}

		# ---------- set on rows ----------
		for row in rows:
			key = (row.item_code, row.warehouse)

			party_name = None
			supplier_date = None

			if key in opening_wh_set:
				# 1. Opening stock
				party_name = OPENING_SUPPLIER
			else:
				# 2 & 3. Purchase based supplier (warehouse level, then item level)
				info = wh_map.get(key) or item_map.get(row.item_code) or {}
				party_name = info.get("supplier")
				supplier_date = info.get("date")

			# 4. Stock Entry / Sales Return / Delivery Note return / no purchase record
			if not party_name:
				party_name = OPENING_SUPPLIER

			row.party_name = party_name
			row.last_stock_in_date = last_in_map.get(key) or supplier_date

		self.set_party_city()

	def set_party_city(self):
		parties = list({r.party_name for r in self.data if r.get("party_name")})
		if not parties:
			return

		city_map = {}

		# 1. Any address linked to the Supplier (primary last => wins)
		addr_rows = frappe.db.sql(
			"""
			SELECT dl.link_name, a.city
			FROM `tabAddress` a
			INNER JOIN `tabDynamic Link` dl
				ON dl.parent = a.name AND dl.parenttype = 'Address'
			WHERE dl.link_doctype = 'Supplier'
				AND dl.link_name IN %(parties)s
				AND IFNULL(a.disabled, 0) = 0
				AND IFNULL(a.city, '') != ''
			ORDER BY a.is_primary_address ASC, a.creation DESC
			""",
			{"parties": parties},
			as_dict=True,
		)
		for d in addr_rows:
			city_map[d.link_name] = d.city

		# 2. Supplier's primary address overrides
		suppliers = frappe.get_all(
			"Supplier",
			filters={"name": ["in", parties]},
			fields=["name", "supplier_primary_address"],
		)
		primary_addrs = {
			s.name: s.supplier_primary_address for s in suppliers if s.supplier_primary_address
		}
		if primary_addrs:
			cities = frappe.get_all(
				"Address",
				filters={"name": ["in", list(primary_addrs.values())]},
				fields=["name", "city"],
			)
			addr_city = {c.name: c.city for c in cities if c.city}
			for supplier, addr in primary_addrs.items():
				if addr_city.get(addr):
					city_map[supplier] = addr_city[addr]

		# 3. TZU Lifestyle Pvt Ltd: agar Supplier address nahi mila to Company ke address ki city
		if OPENING_SUPPLIER in parties and not city_map.get(OPENING_SUPPLIER):
			company_city = frappe.db.sql(
				"""
				SELECT a.city
				FROM `tabAddress` a
				INNER JOIN `tabDynamic Link` dl
					ON dl.parent = a.name AND dl.parenttype = 'Address'
				WHERE dl.link_doctype = 'Company'
					AND (%(company)s IS NULL OR dl.link_name = %(company)s)
					AND IFNULL(a.disabled, 0) = 0
					AND IFNULL(a.city, '') != ''
				ORDER BY a.is_primary_address DESC, a.creation DESC
				LIMIT 1
				""",
				{"company": self.filters.get("company") or None},
			)
			if company_city:
				city_map[OPENING_SUPPLIER] = company_city[0][0]

		for row in self.data:
			row.party_city = city_map.get(row.get("party_name"))

	def get_columns(self):
		columns = [
			{
				"label": _("Item"),
				"fieldname": "item_code",
				"fieldtype": "Link",
				"options": "Item",
				"width": 100,
			},
			{
				"label": _("Item Name"),
				"fieldname": "item_name",
				"width": 150,
			},
			{
				"label": "Image",
				"fieldname": "image",
				"fieldtype": "Data",
				"width": 120,
			},
			{
				"label": _("Style"),
				"fieldname": "style",
				"fieldtype": "Data",
				"width": 100,
			},
			{
				"label": _("Sup Design No."),
				"fieldname": "sup_design_no",
				"fieldtype": "Data",
				"width": 110,
			},
			{
				"label": _("Top Fabric"),
				"fieldname": "top_fabric",
				"fieldtype": "Data",
				"width": 110,
			},
			{
				"label": _("Warehouse"),
				"fieldname": "warehouse",
				"fieldtype": "Link",
				"options": "Warehouse",
				"width": 100,
			},
			{
				"label": _("Party Name"),
				"fieldname": "party_name",
				"fieldtype": "Link",
				"options": "Supplier",
				"width": 180,
			},
			{
				"label": _("Party City"),
				"fieldname": "party_city",
				"fieldtype": "Data",
				"width": 120,
			},
			{
				"label": _("Last Stock In Date"),
				"fieldname": "last_stock_in_date",
				"fieldtype": "Date",
				"width": 120,
			},
			{
				"label": _("Serial No."),
				"fieldname": "serial_no",
				"fieldtype": "Data",
				"width": 210,
			},
			{
				"label": _("Item Group"),
				"fieldname": "item_group",
				"fieldtype": "Link",
				"options": "Item Group",
				"width": 100,
			},
		]

		if self.filters.get("show_dimension_wise_stock"):
			for dimension in get_inventory_dimensions():
				columns.append(
					{
						"label": _(dimension.doctype),
						"fieldname": dimension.fieldname,
						"fieldtype": "Link",
						"options": dimension.doctype,
						"width": 110,
					}
				)

		columns.extend(
			[
				{
					"label": _("Stock UOM"),
					"fieldname": "stock_uom",
					"fieldtype": "Link",
					"options": "UOM",
					"width": 90,
				},
				{
					"label": _("Balance Qty"),
					"fieldname": "bal_qty",
					"fieldtype": "Float",
					"width": 100,
					"convertible": "qty",
				},
				{
					"label": _("Balance Value"),
					"fieldname": "bal_val",
					"fieldtype": "Currency",
					"width": 100,
					"options": "Company:company:default_currency",
				},
				{
					"label": _("Opening Qty"),
					"fieldname": "opening_qty",
					"fieldtype": "Float",
					"width": 100,
					"convertible": "qty",
				},
				{
					"label": _("Opening Value"),
					"fieldname": "opening_val",
					"fieldtype": "Currency",
					"width": 110,
					"options": "Company:company:default_currency",
				},
				{
					"label": _("In Qty"),
					"fieldname": "in_qty",
					"fieldtype": "Float",
					"width": 80,
					"convertible": "qty",
				},
				{
					"label": _("In Value"),
					"fieldname": "in_val",
					"fieldtype": "Float",
					"width": 80,
				},
				{
					"label": _("Out Qty"),
					"fieldname": "out_qty",
					"fieldtype": "Float",
					"width": 80,
					"convertible": "qty",
				},
				{
					"label": _("Out Value"),
					"fieldname": "out_val",
					"fieldtype": "Float",
					"width": 80,
				},
				{
					"label": _("Valuation Rate"),
					"fieldname": "val_rate",
					"fieldtype": self.filters.valuation_field_type or "Currency",
					"width": 90,
					"convertible": "rate",
					"options": (
						"Company:company:default_currency"
						if self.filters.valuation_field_type == "Currency"
						else None
					),
				},
				{
					"label": _("Reserved Stock"),
					"fieldname": "reserved_stock",
					"fieldtype": "Float",
					"width": 80,
					"convertible": "qty",
				},
				{
					"label": _("STD Rate"),
					"fieldname": "std_rate",
					"fieldtype": "Currency",
					"width": 100,
					"options": "Company:company:default_currency",
				},
				{
					"label": _("WSP Rate"),
					"fieldname": "wsp_rate",
					"fieldtype": "Currency",
					"width": 100,
					"options": "Company:company:default_currency",
				},
				{
					"label": _("MRP Rate"),
					"fieldname": "mrp_rate",
					"fieldtype": "Currency",
					"width": 100,
					"options": "Company:company:default_currency",
				},
				{
					"label": _("Company"),
					"fieldname": "company",
					"fieldtype": "Link",
					"options": "Company",
					"width": 100,
				},
			]
		)

		if self.filters.get("show_stock_ageing_data"):
			columns += [
				{"label": _("Average Age"), "fieldname": "average_age", "width": 100},
				{"label": _("Earliest Age"), "fieldname": "earliest_age", "width": 100},
				{"label": _("Latest Age"), "fieldname": "latest_age", "width": 100},
			]

		if self.filters.get("show_variant_attributes"):
			columns += [
				{"label": att_name, "fieldname": att_name, "width": 100}
				for att_name in get_variants_attributes()
			]

		return columns

	def add_additional_uom_columns(self):
		if not self.filters.get("include_uom"):
			return

		conversion_factors = self.get_itemwise_conversion_factor()
		add_additional_uom_columns(self.columns, self.data, self.filters.include_uom, conversion_factors)

	def get_itemwise_conversion_factor(self):
		items = []
		if self.filters.item_code or self.filters.item_group:
			items = [d.item_code for d in self.data]

		table = frappe.qb.DocType("UOM Conversion Detail")
		query = (
			frappe.qb.from_(table)
			.select(
				table.conversion_factor,
				table.parent,
			)
			.where((table.parenttype == "Item") & (table.uom == self.filters.include_uom))
		)

		if items:
			query = query.where(table.parent.isin(items))

		result = query.run(as_dict=1)
		if not result:
			return {}

		return {d.parent: d.conversion_factor for d in result}

	def get_variant_values_for(self):
		"""Returns variant values for items."""
		attribute_map = {}
		items = []
		if self.filters.item_code or self.filters.item_group:
			items = [d.item_code for d in self.data]

		filters = {}
		if items:
			filters = {"parent": ("in", items)}

		attribute_info = frappe.get_all(
			"Item Variant Attribute",
			fields=["parent", "attribute", "attribute_value"],
			filters=filters,
		)

		for attr in attribute_info:
			attribute_map.setdefault(attr["parent"], {})
			attribute_map[attr["parent"]].update({attr["attribute"]: attr["attribute_value"]})

		return attribute_map

	def get_opening_vouchers(self):
		opening_vouchers = {"Stock Entry": [], "Stock Reconciliation": []}

		se = frappe.qb.DocType("Stock Entry")
		sr = frappe.qb.DocType("Stock Reconciliation")

		vouchers_data = (
			frappe.qb.from_(
				(
					frappe.qb.from_(se)
					.select(se.name, Coalesce("Stock Entry").as_("voucher_type"))
					.where((se.docstatus == 1) & (se.posting_date <= self.to_date) & (se.is_opening == "Yes"))
				)
				+ (
					frappe.qb.from_(sr)
					.select(sr.name, Coalesce("Stock Reconciliation").as_("voucher_type"))
					.where(
						(sr.docstatus == 1)
						& (sr.posting_date <= self.to_date)
						& (sr.purpose == "Opening Stock")
					)
				)
			).select("voucher_type", "name")
		).run(as_dict=True)

		if vouchers_data:
			for d in vouchers_data:
				opening_vouchers[d.voucher_type].append(d.name)

		return opening_vouchers

	@staticmethod
	def get_inventory_dimension_fields():
		return [dimension.fieldname for dimension in get_inventory_dimensions()]

	@staticmethod
	def get_opening_fifo_queue(report_data):
		opening_fifo_queue = report_data.get("opening_fifo_queue") or []
		for row in opening_fifo_queue:
			row[1] = getdate(row[1])

		return opening_fifo_queue


def filter_items_with_no_transactions(
	iwb_map, float_precision: float, inventory_dimensions: list | None = None
):
	pop_keys = []
	for group_by_key in iwb_map:
		qty_dict = iwb_map[group_by_key]

		no_transactions = True
		for key, val in qty_dict.items():
			if inventory_dimensions and key in inventory_dimensions:
				continue

			if key in [
				"item_code",
				"warehouse",
				"item_name",
				"item_group",
				"project",
				"stock_uom",
				"company",
				"currency",
				"opening_fifo_queue",
				"style",
				"sup_design_no",
				"top_fabric",
				"image",
			]:
				continue

			val = flt(val, float_precision)
			qty_dict[key] = val
			if key != "val_rate" and val:
				no_transactions = False

		if no_transactions:
			pop_keys.append(group_by_key)

	for key in pop_keys:
		iwb_map.pop(key)

	return iwb_map


def get_variants_attributes() -> list[str]:
	"""Return all item variant attributes."""
	return frappe.get_all("Item Attribute", pluck="name")