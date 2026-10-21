import json

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})

	columns = get_columns()
	data = get_data(filters)

	return columns, data


# ============================================================
# COLUMNS
# ============================================================

def get_columns():
	return [
		{
			"label": _("Sales Invoice"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Sales Invoice",
			"width": 160,
		},
		{
			"label": _("Posting Date"),
			"fieldname": "posting_date",
			"fieldtype": "Date",
			"width": 110,
		},
		{
			"label": _("Customer Name"),
			"fieldname": "customer_name",
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"label": _("Customer Agent"),
			"fieldname": "customer_agent",
			"fieldtype": "Link",
			"options": "Supplier",
			"width": 180,
		},
		{
			"label": _("Customer Group"),
			"fieldname": "customer_group",
			"fieldtype": "Link",
			"options": "Customer Group",
			"width": 180,
		},
		{
			"label": _("Supplier Name"),
			"fieldname": "supplier_name",
			"fieldtype": "Link",
			"options": "Supplier",
			"width": 180,
		},
		{
			"label": _("Supplier Agent"),
			"fieldname": "supplier_agent",
			"fieldtype": "Link",
			"options": "Supplier",
			"width": 180,
		},
		{
			"label": _("Item Code"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 140,
		},
		{
			"label": _("Class Name"),
			"fieldname": "class_name",
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"label": _("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"width": 150,
		},
		{
			"label": _("Item Name"),
			"fieldname": "item_name",
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"label": _("Serial No"),
			"fieldname": "serial_no",
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"label": _("Quantity"),
			"fieldname": "qty",
			"fieldtype": "Float",
			"width": 100,
		},
		{
			"label": _("Rate"),
			"fieldname": "rate",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 110,
		},
		{
			"label": _("Gross Amount"),
			"fieldname": "gross_amount",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 130,
		},
		{
			"label": _("Net Amount"),
			"fieldname": "net_amount",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 130,
		},
		{
			"label": _("Currency"),
			"fieldname": "currency",
			"fieldtype": "Data",
			"width": 90,
		},
		{
			"label": _("Bottom Fabric"),
			"fieldname": "custom_bottom_fabric",
			"fieldtype": "Data",
			"width": 160,
		},
		{
			"label": _("Dupatta Fabric"),
			"fieldname": "custom_dupatta_fabric",
			"fieldtype": "Data",
			"width": 170,
		},
		{
			"label": _("Top Fabric"),
			"fieldname": "custom_top_fabric",
			"fieldtype": "Data",
			"width": 160,
		},
		{
			"label": _("MRP"),
			"fieldname": "custom_mrp",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120,
		},
		{
			"label": _("Count Of Pcs"),
			"fieldname": "custom_count_of_pcs",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": _("Sup Design No."),
			"fieldname": "sup_design_no",
			"fieldtype": "Data",
			"width": 170,
		},
	]


# ============================================================
# DATA
# ============================================================

def get_data(filters):
	si = frappe.qb.DocType("Sales Invoice")
	sii = frappe.qb.DocType("Sales Invoice Item")
	item = frappe.qb.DocType("Item")
	customer = frappe.qb.DocType("Customer")

	query = (
		frappe.qb.from_(si)
		.inner_join(sii)
		.on(sii.parent == si.name)
		.left_join(item)
		.on(item.name == sii.item_code)
		.left_join(customer)
		.on(customer.name == si.customer)
		.select(
			# ---------------- SALES INVOICE ----------------
			si.name,
			si.posting_date,
			si.customer,
			si.customer_name,
			si.custom_class_name.as_("class_name"),
			si.company,
			si.currency,
			si.is_return,
			si.return_against,

			# Net Total: discount ke baad, GST ke pehle
			si.net_total.as_("gross_amount"),

			# Rounded Total: GST included final amount
			si.rounded_total.as_("net_amount"),

			# ---------------- CUSTOMER ----------------
			customer.custom_agent.as_("customer_agent"),
			customer.customer_group.as_("customer_group"),

			# ---------------- SALES INVOICE ITEM ----------------
			sii.name.as_("sales_invoice_item"),
			sii.item_code,
			sii.item_name,
			sii.serial_no,
			sii.serial_and_batch_bundle,
			sii.batch_no,
			sii.qty,
			sii.rate,
			sii.amount,

			# ---------------- CUSTOM ITEM FIELDS ----------------
			sii.custom_bottom_fabric,
			sii.custom_dupatta_fabric,
			sii.custom_top_fabric,
			sii.custom_mrp,
			sii.custom_count_of_pcs,

			# ---------------- ITEM ----------------
			item.custom_sup_design_no.as_("sup_design_no"),
		)
		.where(si.docstatus == 1)
	)

	# ---------------- DATE FILTER ----------------
	if filters.get("from_date"):
		query = query.where(si.posting_date >= filters.get("from_date"))

	if filters.get("to_date"):
		query = query.where(si.posting_date <= filters.get("to_date"))

	# ---------------- CUSTOMER FILTER ----------------
	customers = get_filter_list(filters.get("customer"))
	if customers:
		query = query.where(si.customer.isin(customers))

	# ---------------- CUSTOMER GROUP FILTER ----------------
	customer_groups = get_filter_list(filters.get("customer_group"))
	if customer_groups:
		query = query.where(customer.customer_group.isin(customer_groups))

	# ---------------- CLASS NAME FILTER ----------------
	class_names = get_filter_list(filters.get("class_name"))
	if class_names:
		query = query.where(si.custom_class_name.isin(class_names))

	# ---------------- SALES INVOICE FILTER ----------------
	invoice_ids = get_filter_list(
		filters.get("sales_invoice") or filters.get("id")
	)
	if invoice_ids:
		query = query.where(si.name.isin(invoice_ids))

	# ---------------- CUSTOMER AGENT FILTER ----------------
	agents = get_filter_list(filters.get("agent"))
	if agents:
		query = query.where(customer.custom_agent.isin(agents))

	data = query.orderby(
		si.posting_date,
		order=frappe.qb.desc
	).run(as_dict=True)

	# ---------------- SUPPLIER LOOKUP (BULK) ----------------
	frappe.local.cs_supplier_cache = {}

	suppliers = bulk_resolve_suppliers(data)

	for row in data:
		supplier = suppliers.get(row.get("sales_invoice_item"))

		row["supplier_name"] = supplier
		row["supplier_agent"] = get_supplier_agent(supplier)

	return data


# ============================================================
# HELPERS
# ============================================================

def _cache():
	if not hasattr(frappe.local, "cs_supplier_cache"):
		frappe.local.cs_supplier_cache = {}

	return frappe.local.cs_supplier_cache


def _chunks(items, size=1000):
	items = list(items)

	for i in range(0, len(items), size):
		yield items[i:i + size]


TZU_COMPANY = "TZU Lifestyle Private Limited"
TZU_SUPPLIER = "TZU Lifestyle Pvt Ltd"

# False  -> Opening Stock sirf TZU company ka ho tabhi supplier = TZU
# True   -> kisi bhi company (franchise) ka Opening Stock ho to bhi supplier = TZU
OPENING_STOCK_ANY_COMPANY = True

VOUCHER_TYPES = (
	"Purchase Receipt",
	"Purchase Invoice",
	"Subcontracting Receipt",
	"Stock Reconciliation",
	"Stock Entry",
)


# ============================================================
# SUPPLIER AGENT
# ============================================================

def get_supplier_agent(supplier):
	if not supplier:
		return None

	cache = _cache()
	key = ("agent", supplier)

	if key in cache:
		return cache[key]

	agent = None

	if frappe.db.has_column("Supplier", "custom_agent_supplier"):
		agent = frappe.db.get_value(
			"Supplier",
			supplier,
			"custom_agent_supplier"
		)

	cache[key] = agent
	return agent


# ============================================================
# BULK RESOLVER (MAIN)
# ============================================================

def bulk_resolve_suppliers(rows):
	"""
	Returns {sales_invoice_item_name: supplier}
	Saari rows ke serial/batch ek saath collect karke
	chunk me query karta hai (row-by-row queries nahi).
	"""

	# ---------- 1. Return invoices ke original items ----------
	return_parents = {
		r.get("return_against")
		for r in rows
		if r.get("is_return") and r.get("return_against")
	}

	originals = {}

	for chunk in _chunks(return_parents):
		for o in frappe.get_all(
			"Sales Invoice Item",
			filters={"parent": ["in", chunk]},
			fields=[
				"parent",
				"item_code",
				"serial_no",
				"serial_and_batch_bundle",
				"batch_no",
			],
		):
			originals.setdefault(
				(o.parent, o.item_code), []
			).append(o)

	# ---------- 2. Saare bundles expand karo ----------
	bundles = set()

	for r in rows:
		if r.get("serial_and_batch_bundle"):
			bundles.add(r.get("serial_and_batch_bundle"))

	for items in originals.values():
		for o in items:
			if o.serial_and_batch_bundle:
				bundles.add(o.serial_and_batch_bundle)

	bundle_map = {}

	if bundles and frappe.db.exists("DocType", "Serial and Batch Entry"):
		for chunk in _chunks(bundles):
			for e in frappe.get_all(
				"Serial and Batch Entry",
				filters={"parent": ["in", chunk]},
				fields=["parent", "serial_no", "batch_no"],
			):
				entry = bundle_map.setdefault(e.parent, ([], []))

				if e.serial_no:
					entry[0].append(e.serial_no)

				if e.batch_no:
					entry[1].append(e.batch_no)

	def collect(serial_no, bundle, batch_no):
		serials = split_serial_numbers(serial_no)
		batches = [batch_no] if batch_no else []

		if bundle and bundle in bundle_map:
			serials += [s for s in bundle_map[bundle][0] if s not in serials]
			batches += [b for b in bundle_map[bundle][1] if b not in batches]

		return serials, batches

	# ---------- 3. Har row ke serial / batch ----------
	row_info = {}
	all_serials = set()
	all_batches = set()

	for r in rows:
		own_serials, own_batches = collect(
			r.get("serial_no"),
			r.get("serial_and_batch_bundle"),
			r.get("batch_no"),
		)

		orig_serials = []
		orig_batches = []

		if r.get("is_return") and r.get("return_against"):
			for o in originals.get(
				(r.get("return_against"), r.get("item_code")), []
			):
				s, b = collect(
					o.serial_no,
					o.serial_and_batch_bundle,
					o.batch_no,
				)
				orig_serials += s
				orig_batches += b

		row_info[r.get("sales_invoice_item")] = (
			own_serials,
			own_batches,
			orig_serials,
			orig_batches,
		)

		all_serials.update(own_serials)
		all_serials.update(orig_serials)
		all_batches.update(own_batches)
		all_batches.update(orig_batches)

	# ---------- 4. Bulk serial / batch -> supplier ----------
	serial_supplier = map_serials_to_suppliers(all_serials)
	batch_supplier = map_batches_to_suppliers(all_batches)

	# ---------- 5. Row wise resolve (memory me) ----------
	result = {}

	for r in rows:
		key = r.get("sales_invoice_item")
		item_code = r.get("item_code")

		own_serials, own_batches, orig_serials, orig_batches = row_info[key]

		supplier = None

		# own serials
		for s in own_serials:
			supplier = serial_supplier.get(s)
			if supplier:
				break

		# own batches
		if not supplier:
			for b in own_batches:
				supplier = batch_supplier.get(b)
				if supplier:
					break

		# return -> original invoice serials / batches
		if not supplier:
			for s in orig_serials:
				supplier = serial_supplier.get(s)
				if supplier:
					break

		if not supplier:
			for b in orig_batches:
				supplier = batch_supplier.get(b)
				if supplier:
					break

		# TZU sales return special case (sirf unresolved rows)
		if not supplier:
			for s in own_serials:
				supplier = get_supplier_from_sales_return_company(
					item_code,
					s
				)
				if supplier:
					break

		# item level fallback (cached per item)
		if not supplier:
			supplier = get_supplier_item_level(item_code)

		result[key] = supplier

	return result


# ============================================================
# DOCUMENT NO -> SUPPLIER (BULK)
# ============================================================

def get_doc_suppliers(doc_names):
	result = {}

	doc_names = [d for d in set(doc_names) if d]

	if not doc_names:
		return result

	specs = [
		("Purchase Receipt", True),
		("Purchase Invoice", True),
		("Purchase Order", True),
		("Subcontracting Receipt", False),
	]

	custom_doctypes = [
		"Stock Reconciliation",
		"Stock Entry",
		"Opening Stock",
	]

	possible_fields = [
		"supplier",
		"custom_supplier",
		"default_supplier",
	]

	for chunk in _chunks(doc_names):
		for doctype, submitted_only in specs:
			if not frappe.db.exists("DocType", doctype):
				continue

			pending = [n for n in chunk if n not in result]

			if not pending:
				break

			filters = {"name": ["in", pending]}

			if submitted_only:
				filters["docstatus"] = 1

			for d in frappe.get_all(
				doctype,
				filters=filters,
				fields=["name", "supplier"],
			):
				if d.supplier:
					result[d.name] = d.supplier

		for doctype in custom_doctypes:
			if not frappe.db.exists("DocType", doctype):
				continue

			fields = [
				f for f in possible_fields
				if frappe.db.has_column(doctype, f)
			]

			if not fields:
				continue

			pending = [n for n in chunk if n not in result]

			if not pending:
				break

			for d in frappe.get_all(
				doctype,
				filters={"name": ["in", pending]},
				fields=["name"] + fields,
			):
				for f in fields:
					if d.get(f):
						result[d.name] = d.get(f)
						break

	return result


def _assign(result, docs_map, seen=None):
	"""docs_map = {key: [doc_no, ...]} -> result[key] = supplier"""
	if seen is not None:
		for key, docs in docs_map.items():
			seen.setdefault(key, []).extend(docs)

	all_docs = {d for docs in docs_map.values() for d in docs}
	doc_supplier = get_doc_suppliers(all_docs)

	for key, docs in docs_map.items():
		if key in result:
			continue

		for d in docs:
			if doc_supplier.get(d):
				result[key] = doc_supplier[d]
				break


# ============================================================
# OPENING STOCK DOCUMENTS (TZU company) -> TZU supplier
# ============================================================

def get_opening_stock_docs(doc_names):
	"""
	Un documents ka set jo TZU company ke Opening Stock hain:
	- Stock Reconciliation  (purpose = Opening Stock)
	- Stock Entry           (is_opening = Yes / purpose = Opening Stock)
	"""
	found = set()

	doc_names = [d for d in set(doc_names) if d]

	if not doc_names:
		return found

	for chunk in _chunks(doc_names):
		# Stock Reconciliation
		if frappe.db.exists("DocType", "Stock Reconciliation"):
			for d in frappe.get_all(
				"Stock Reconciliation",
				filters=_opening_filters(
					{
						"name": ["in", chunk],
						"docstatus": 1,
						"purpose": "Opening Stock",
					}
				),
				fields=["name"],
			):
				found.add(d.name)

		# Stock Entry
		pending = [n for n in chunk if n not in found]

		if pending and frappe.db.exists("DocType", "Stock Entry"):
			conditions = []

			if frappe.db.has_column("Stock Entry", "is_opening"):
				conditions.append(["is_opening", "=", "Yes"])

			if frappe.db.has_column("Stock Entry", "purpose"):
				conditions.append(["purpose", "=", "Opening Stock"])

			for cond in conditions:
				for d in frappe.get_all(
					"Stock Entry",
					filters=(
						[
							["name", "in", pending],
							["docstatus", "=", 1],
							cond,
						]
						+ (
							[]
							if OPENING_STOCK_ANY_COMPANY
							else [["company", "=", TZU_COMPANY]]
						)
					),
					fields=["name"],
				):
					found.add(d.name)

	return found


def _opening_filters(filters):
	if not OPENING_STOCK_ANY_COMPANY:
		filters["company"] = TZU_COMPANY

	return filters


def _tzu_supplier():
	cache = _cache()

	if "tzu_supplier" not in cache:
		cache["tzu_supplier"] = (
			TZU_SUPPLIER
			if frappe.db.exists("Supplier", TZU_SUPPLIER)
			else None
		)

	return cache["tzu_supplier"]


def _assign_opening(result, seen):
	"""
	Real supplier nahi mila, aur serial/batch ka source document
	TZU ka Opening Stock hai -> TZU Lifestyle Pvt Ltd
	"""
	tzu = _tzu_supplier()

	if not tzu:
		return

	pending = {k: docs for k, docs in seen.items() if k not in result}

	if not pending:
		return

	all_docs = {d for docs in pending.values() for d in docs}
	opening_docs = get_opening_stock_docs(all_docs)

	for key, docs in pending.items():
		if any(d in opening_docs for d in docs):
			result[key] = tzu


# ============================================================
# SERIALS -> SUPPLIER (BULK)
# ============================================================

def map_serials_to_suppliers(serials):
	result = {}
	seen = {}

	serials = [s for s in set(serials) if s]

	if not serials:
		return result

	# ---- A. Serial No master (purchase / creation document) ----
	fields = ["name", "purchase_document_no"]

	if frappe.db.has_column("Serial No", "creation_document_no"):
		fields.append("creation_document_no")

	docs_map = {}

	for chunk in _chunks(serials):
		for r in frappe.get_all(
			"Serial No",
			filters={"name": ["in", chunk]},
			fields=fields,
		):
			docs = [
				d for d in (
					r.get("purchase_document_no"),
					r.get("creation_document_no"),
				) if d
			]

			if docs:
				docs_map[r.name] = docs

	_assign(result, docs_map, seen)

	# ---- B. Serial and Batch Entry + Stock Ledger (v15) ----
	pending = [s for s in serials if s not in result]

	if pending and frappe.db.exists("DocType", "Serial and Batch Entry"):
		docs_map = {}

		for chunk in _chunks(pending):
			entries = frappe.db.sql(
				"""
				SELECT
					sbe.serial_no,
					sle.voucher_no
				FROM
					`tabSerial and Batch Entry` sbe
				INNER JOIN
					`tabStock Ledger Entry` sle
					ON sle.serial_and_batch_bundle = sbe.parent
				WHERE
					sbe.serial_no IN %(serials)s
					AND sle.is_cancelled = 0
					AND sle.actual_qty > 0
					AND sle.voucher_type IN %(types)s
				ORDER BY
					sle.posting_date ASC,
					sle.posting_time ASC,
					sle.creation ASC
				""",
				{"serials": tuple(chunk), "types": VOUCHER_TYPES},
				as_dict=True,
			)

			for e in entries:
				docs_map.setdefault(e.serial_no, []).append(e.voucher_no)

		_assign(result, docs_map, seen)

	# ---- C. Legacy Stock Ledger (single serial entries) ----
	pending = [s for s in serials if s not in result]

	if pending and frappe.db.has_column("Stock Ledger Entry", "serial_no"):
		docs_map = {}

		for chunk in _chunks(pending):
			entries = frappe.db.sql(
				"""
				SELECT
					serial_no,
					voucher_no
				FROM
					`tabStock Ledger Entry`
				WHERE
					serial_no IN %(serials)s
					AND is_cancelled = 0
					AND actual_qty > 0
					AND voucher_type IN %(types)s
				ORDER BY
					posting_date ASC,
					posting_time ASC,
					creation ASC
				""",
				{"serials": tuple(chunk), "types": VOUCHER_TYPES},
				as_dict=True,
			)

			for e in entries:
				docs_map.setdefault(e.serial_no, []).append(e.voucher_no)

		_assign(result, docs_map, seen)

	_assign_opening(result, seen)

	return result


# ============================================================
# BATCHES -> SUPPLIER (BULK)
# ============================================================

def map_batches_to_suppliers(batches):
	result = {}
	seen = {}

	batches = [b for b in set(batches) if b]

	if not batches:
		return result

	# ---- A. Batch master reference ----
	docs_map = {}

	for chunk in _chunks(batches):
		for b in frappe.get_all(
			"Batch",
			filters={"name": ["in", chunk]},
			fields=["name", "reference_name"],
		):
			if b.reference_name:
				docs_map[b.name] = [b.reference_name]

	_assign(result, docs_map, seen)

	# ---- B. Stock Ledger (batch_no direct) ----
	pending = [b for b in batches if b not in result]

	if pending and frappe.db.has_column("Stock Ledger Entry", "batch_no"):
		docs_map = {}

		for chunk in _chunks(pending):
			entries = frappe.db.sql(
				"""
				SELECT
					batch_no,
					voucher_no
				FROM
					`tabStock Ledger Entry`
				WHERE
					batch_no IN %(batches)s
					AND is_cancelled = 0
					AND actual_qty > 0
					AND voucher_type IN %(types)s
				ORDER BY
					posting_date ASC,
					posting_time ASC,
					creation ASC
				""",
				{"batches": tuple(chunk), "types": VOUCHER_TYPES},
				as_dict=True,
			)

			for e in entries:
				docs_map.setdefault(e.batch_no, []).append(e.voucher_no)

		_assign(result, docs_map, seen)

	# ---- C. Serial and Batch Entry + Stock Ledger (v15) ----
	pending = [b for b in batches if b not in result]

	if pending and frappe.db.exists("DocType", "Serial and Batch Entry"):
		docs_map = {}

		for chunk in _chunks(pending):
			entries = frappe.db.sql(
				"""
				SELECT
					sbe.batch_no,
					sle.voucher_no
				FROM
					`tabSerial and Batch Entry` sbe
				INNER JOIN
					`tabStock Ledger Entry` sle
					ON sle.serial_and_batch_bundle = sbe.parent
				WHERE
					sbe.batch_no IN %(batches)s
					AND sle.is_cancelled = 0
					AND sle.actual_qty > 0
					AND sle.voucher_type IN %(types)s
				ORDER BY
					sle.posting_date ASC,
					sle.posting_time ASC,
					sle.creation ASC
				""",
				{"batches": tuple(chunk), "types": VOUCHER_TYPES},
				as_dict=True,
			)

			for e in entries:
				docs_map.setdefault(e.batch_no, []).append(e.voucher_no)

		_assign(result, docs_map, seen)

	_assign_opening(result, seen)

	return result


# ============================================================
# ITEM LEVEL FALLBACK (cached per item)
# ============================================================

def get_supplier_item_level(item_code):
	if not item_code:
		return None

	cache = _cache()
	key = ("item", item_code)

	if key in cache:
		return cache[key]

	supplier = (
		get_supplier_from_item_supplier(item_code)
		or get_supplier_from_item_stock_ledger(item_code)
		or get_supplier_from_purchase_history(item_code)
		or get_supplier_from_purchase_invoice_history(item_code)
		or get_supplier_from_subcontracting_history(item_code)
		or get_supplier_from_purchase_order_history(item_code)
		or get_supplier_from_draft_purchase_docs(item_code)
		or get_supplier_from_item_opening_stock(item_code)
		or get_supplier_from_item_stock_in(item_code)
	)

	cache[key] = supplier
	return supplier


def get_supplier_from_item_supplier(item_code):
	result = frappe.db.sql(
		"""
		SELECT supplier
		FROM `tabItem Supplier`
		WHERE parent = %(item_code)s
			AND IFNULL(supplier, '') != ''
		ORDER BY idx ASC
		LIMIT 1
		""",
		{"item_code": item_code},
		as_dict=True,
	)

	if result:
		return result[0].get("supplier")

	if frappe.db.has_column("Item", "default_supplier"):
		supplier = frappe.db.get_value(
			"Item", item_code, "default_supplier"
		)

		if supplier:
			return supplier

	return None


def get_supplier_from_item_stock_ledger(item_code):
	entries = frappe.db.sql(
		"""
		SELECT voucher_no
		FROM `tabStock Ledger Entry`
		WHERE is_cancelled = 0
			AND item_code = %(item_code)s
			AND actual_qty > 0
			AND voucher_type IN %(types)s
		ORDER BY posting_date ASC, posting_time ASC
		LIMIT 5
		""",
		{"item_code": item_code, "types": VOUCHER_TYPES},
		as_dict=True,
	)

	doc_supplier = get_doc_suppliers([e.voucher_no for e in entries])

	for e in entries:
		if doc_supplier.get(e.voucher_no):
			return doc_supplier[e.voucher_no]

	return None


def get_supplier_from_purchase_history(item_code):
	result = frappe.db.sql(
		"""
		SELECT pr.supplier
		FROM `tabPurchase Receipt Item` pri
		INNER JOIN `tabPurchase Receipt` pr ON pr.name = pri.parent
		WHERE pr.docstatus = 1
			AND pri.item_code = %(item_code)s
			AND IFNULL(pr.supplier, '') != ''
		ORDER BY pr.posting_date DESC, pr.creation DESC
		LIMIT 1
		""",
		{"item_code": item_code},
		as_dict=True,
	)

	if result:
		return result[0].get("supplier")

	return None


def get_supplier_from_purchase_invoice_history(item_code):
	result = frappe.db.sql(
		"""
		SELECT pi.supplier
		FROM `tabPurchase Invoice Item` pii
		INNER JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
		WHERE pi.docstatus = 1
			AND pii.item_code = %(item_code)s
			AND IFNULL(pi.supplier, '') != ''
		ORDER BY pi.posting_date DESC, pi.creation DESC
		LIMIT 1
		""",
		{"item_code": item_code},
		as_dict=True,
	)

	if result:
		return result[0].get("supplier")

	return None


def get_supplier_from_subcontracting_history(item_code):
	if not frappe.db.exists("DocType", "Subcontracting Receipt Item"):
		return None

	result = frappe.db.sql(
		"""
		SELECT sr.supplier
		FROM `tabSubcontracting Receipt Item` sri
		INNER JOIN `tabSubcontracting Receipt` sr ON sr.name = sri.parent
		WHERE sr.docstatus = 1
			AND sri.item_code = %(item_code)s
			AND IFNULL(sr.supplier, '') != ''
		ORDER BY sr.posting_date DESC, sr.creation DESC
		LIMIT 1
		""",
		{"item_code": item_code},
		as_dict=True,
	)

	if result:
		return result[0].get("supplier")

	return None


def get_supplier_from_purchase_order_history(item_code):
	result = frappe.db.sql(
		"""
		SELECT po.supplier
		FROM `tabPurchase Order Item` poi
		INNER JOIN `tabPurchase Order` po ON po.name = poi.parent
		WHERE po.docstatus = 1
			AND poi.item_code = %(item_code)s
			AND IFNULL(po.supplier, '') != ''
		ORDER BY po.transaction_date DESC, po.creation DESC
		LIMIT 1
		""",
		{"item_code": item_code},
		as_dict=True,
	)

	if result:
		return result[0].get("supplier")

	return None


def get_supplier_from_item_opening_stock(item_code):
	"""
	Item ka stock TZU ke Opening Stock (Stock Reconciliation /
	Stock Entry) se aaya hai -> TZU Lifestyle Pvt Ltd
	"""
	tzu = _tzu_supplier()

	if not tzu:
		return None

	# Stock Reconciliation (purpose = Opening Stock)
	if frappe.db.sql(
		"""
		SELECT sri.name
		FROM `tabStock Reconciliation Item` sri
		INNER JOIN `tabStock Reconciliation` sr ON sr.name = sri.parent
		WHERE sr.docstatus = 1
			AND sr.purpose = 'Opening Stock'
			AND (%(any_company)s = 1 OR sr.company = %(company)s)
			AND sri.item_code = %(item_code)s
		LIMIT 1
		""",
		{
			"item_code": item_code,
			"company": TZU_COMPANY,
			"any_company": 1 if OPENING_STOCK_ANY_COMPANY else 0,
		},
	):
		return tzu

	# Stock Entry (opening)
	if frappe.db.has_column("Stock Entry", "is_opening"):
		if frappe.db.sql(
			"""
			SELECT sed.name
			FROM `tabStock Entry Detail` sed
			INNER JOIN `tabStock Entry` se ON se.name = sed.parent
			WHERE se.docstatus = 1
				AND se.is_opening = 'Yes'
				AND (%(any_company)s = 1 OR se.company = %(company)s)
				AND sed.item_code = %(item_code)s
			LIMIT 1
			""",
			{
				"item_code": item_code,
				"company": TZU_COMPANY,
				"any_company": 1 if OPENING_STOCK_ANY_COMPANY else 0,
			},
		):
			return tzu

	return None


def get_supplier_from_draft_purchase_docs(item_code):
	"""
	Submitted nahi hue (draft) Purchase Order / Receipt / Invoice
	jinme supplier bhara hai (cancelled ignore).
	"""
	for parent_dt, child_dt, date_field in (
		("Purchase Order", "Purchase Order Item", "transaction_date"),
		("Purchase Receipt", "Purchase Receipt Item", "posting_date"),
		("Purchase Invoice", "Purchase Invoice Item", "posting_date"),
	):
		result = frappe.db.sql(
			f"""
			SELECT p.supplier
			FROM `tab{child_dt}` c
			INNER JOIN `tab{parent_dt}` p ON p.name = c.parent
			WHERE p.docstatus < 2
				AND c.item_code = %(item_code)s
				AND IFNULL(p.supplier, '') != ''
			ORDER BY p.{date_field} DESC, p.creation DESC
			LIMIT 1
			""",
			{"item_code": item_code},
			as_dict=True,
		)

		if result:
			return result[0].get("supplier")

	return None


# Last resort: item ka stock TZU me Stock Entry / Stock Reconciliation
# (kisi bhi purpose se) se aaya hai aur koi purchase supplier nahi mila.
# Agar ye rule nahi chahiye to False kar do.
TZU_FOR_STOCK_IN_FALLBACK = True


def get_supplier_from_item_stock_in(item_code):
	if not TZU_FOR_STOCK_IN_FALLBACK:
		return None

	tzu = _tzu_supplier()

	if not tzu:
		return None

	if frappe.db.sql(
		"""
		SELECT name
		FROM `tabStock Ledger Entry`
		WHERE item_code = %(item_code)s
			AND company = %(company)s
			AND is_cancelled = 0
			AND actual_qty > 0
			AND voucher_type IN ('Stock Entry', 'Stock Reconciliation')
		LIMIT 1
		""",
		{"item_code": item_code, "company": TZU_COMPANY},
	):
		return tzu

	return None


# ============================================================
# SALES RETURN -> WAREHOUSE COMPANY -> SUPPLIER (TZU special)
# (sirf unresolved rows ke liye chalta hai)
# ============================================================

def get_supplier_from_sales_return_company(item_code, serial_no):
	if not item_code or not serial_no:
		return None

	purchase_document_no = frappe.db.get_value(
		"Serial No",
		{"serial_no": serial_no, "item_code": item_code},
		"purchase_document_no"
	)

	if not purchase_document_no:
		return None

	sales_return = frappe.db.get_value(
		"Sales Invoice",
		{
			"name": purchase_document_no,
			"docstatus": 1,
			"is_return": 1,
		},
		["name", "return_against", "set_warehouse"],
		as_dict=True,
	)

	if not sales_return:
		return None

	return_item = frappe.db.get_value(
		"Sales Invoice Item",
		{
			"parent": sales_return.name,
			"item_code": item_code,
		},
		[
			"name",
			"warehouse",
			"delivery_note",
			"dn_detail",
			"sales_order",
			"so_detail",
		],
		as_dict=True,
	)

	if not return_item:
		return None

	if (
		return_item.delivery_note
		or return_item.dn_detail
		or return_item.sales_order
		or return_item.so_detail
	):
		return None

	warehouse = return_item.warehouse

	if not warehouse:
		warehouse = sales_return.set_warehouse

	if not warehouse:
		warehouse = get_warehouse_for_serial(item_code, serial_no)

	if not warehouse:
		return None

	company = frappe.db.get_value("Warehouse", warehouse, "company")

	if company != "TZU Lifestyle Private Limited":
		return None

	supplier = "TZU Lifestyle Pvt Ltd"

	if frappe.db.exists("Supplier", supplier):
		return supplier

	return None


def get_warehouse_for_serial(item_code, serial_no):
	if not item_code or not serial_no:
		return None

	warehouse = frappe.db.get_value(
		"Serial No",
		{"serial_no": serial_no, "item_code": item_code},
		"warehouse"
	)

	if warehouse:
		return warehouse

	entries = frappe.db.sql(
		"""
		SELECT
			sed.s_warehouse,
			sed.t_warehouse
		FROM
			`tabStock Entry` se
		INNER JOIN
			`tabStock Entry Detail` sed
			ON sed.parent = se.name
		WHERE
			se.docstatus = 1
			AND sed.item_code = %(item_code)s
			AND (
				sed.serial_no = %(serial_no)s
				OR FIND_IN_SET(
					%(serial_no)s,
					REPLACE(
						REPLACE(
							IFNULL(sed.serial_no, ''),
							'\\n',
							','
						),
						'\\r',
						''
					)
				) > 0
			)
		ORDER BY
			se.posting_date DESC,
			se.posting_time DESC,
			se.creation DESC
		LIMIT 20
		""",
		{"item_code": item_code, "serial_no": serial_no},
		as_dict=True,
	)

	for entry in entries:
		if entry.get("t_warehouse"):
			return entry.get("t_warehouse")

	for entry in entries:
		if entry.get("s_warehouse"):
			return entry.get("s_warehouse")

	return None


# ============================================================
# SPLIT SERIAL NUMBERS
# ============================================================

def split_serial_numbers(serial_no):
	if not serial_no:
		return []

	if isinstance(serial_no, list):
		return serial_no

	serial_no = str(serial_no)
	serial_no = serial_no.replace("\r", "\n")
	serial_no = serial_no.replace(",", "\n")

	return [
		x.strip()
		for x in serial_no.split("\n")
		if x.strip()
	]


# ============================================================
# FILTER LIST
# ============================================================

def get_filter_list(value):
	if not value:
		return []

	if isinstance(value, list):
		return value

	if isinstance(value, str):
		try:
			parsed_value = json.loads(value)

			if isinstance(parsed_value, list):
				return parsed_value

		except Exception:
			pass

		return [
			x.strip()
			for x in value.split(",")
			if x.strip()
		]

	return [value]
