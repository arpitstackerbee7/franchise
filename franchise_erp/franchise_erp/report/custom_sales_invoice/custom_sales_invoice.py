import frappe
from frappe import _
import json



def execute(filters=None):
	filters = frappe._dict(filters or {})

	columns = get_columns()
	data = get_data(filters)

	return columns, data



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
			"label": _("Customer"),
			"fieldname": "customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 160,
		},
		{
			"label": _("Customer Name"),
			"fieldname": "customer_name",
			"fieldtype": "Data",
			"width": 180,
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
			"label": _("Item Code"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 140,
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
			"label": _("Amount"),
			"fieldname": "amount",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120,
		},
		{
			"label": _("Grand Total"),
			"fieldname": "grand_total",
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
			"label": _("Supplier Name"),
			"fieldname": "supplier_name",
			"fieldtype": "Link",
			"options": "Supplier",
			"width": 180,
		},
		{
			"label": _("Sup Design No."),
			"fieldname": "sup_design_no",
			"fieldtype": "Data",
			"width": 170,
		},
		{
			"label": _("Agent Supplier"),
			"fieldname": "agent_supplier",
			"fieldtype": "Link",
			"options": "Supplier",
			"width": 180,
		},
	]


def get_data(filters):

	si = frappe.qb.DocType("Sales Invoice")
	sii = frappe.qb.DocType("Sales Invoice Item")
	item = frappe.qb.DocType("Item")

	query = (
		frappe.qb.from_(si)
		.inner_join(sii)
		.on(sii.parent == si.name)

		.left_join(item)
		.on(item.name == sii.item_code)

		.select(

			# SALES INVOICE
			si.name,
			si.posting_date,
			si.customer,
			si.customer_name,
			si.custom_class_name.as_("class_name"),
			si.company,
			si.grand_total,
			si.currency,

			# SALES INVOICE ITEM
			sii.name.as_("sales_invoice_item"),
			sii.item_code,
			sii.item_name,
			sii.serial_no,
			sii.qty,
			sii.rate,
			sii.amount,

			# CUSTOM FIELDS
			sii.custom_bottom_fabric,
			sii.custom_dupatta_fabric,
			sii.custom_top_fabric,
			sii.custom_mrp,
			sii.custom_count_of_pcs,

			# ITEM MASTER
			item.custom_sup_design_no.as_("sup_design_no"),
		)

		.where(si.docstatus == 1)
	)


	if filters.get("from_date"):
		query = query.where(
			si.posting_date >= filters.get("from_date")
		)

	if filters.get("to_date"):
		query = query.where(
			si.posting_date <= filters.get("to_date")
		)


	customers = get_filter_list(filters.get("customer"))

	if customers:
		query = query.where(
			si.customer.isin(customers)
		)


	class_names = get_filter_list(
		filters.get("class_name")
	)

	if class_names:
		query = query.where(
			si.custom_class_name.isin(class_names)
		)


	invoice_ids = get_filter_list(
		filters.get("sales_invoice")
		or filters.get("id")
	)

	if invoice_ids:
		query = query.where(
			si.name.isin(invoice_ids)
		)


	data = query.orderby(
		si.posting_date,
		order=frappe.qb.desc
	).run(as_dict=True)


	for row in data:

		supplier = get_supplier_for_item(
			item_code=row.get("item_code"),
			serial_no=row.get("serial_no"),
		)

		row["supplier_name"] = supplier

		if supplier:
			row["agent_supplier"] = frappe.db.get_value(
				"Supplier",
				supplier,
				"custom_agent_supplier"
			)
		else:
			row["agent_supplier"] = None


	agents = get_filter_list(
		filters.get("agent_supplier")
		or filters.get("agent")
	)

	if agents:
		data = [
			row
			for row in data
			if row.get("agent_supplier") in agents
		]

	return data


def get_supplier_for_item(item_code, serial_no):


	serial_numbers = split_serial_numbers(serial_no)


	for serial in serial_numbers:

		supplier = get_supplier_from_purchase_receipt_serial(
			item_code,
			serial
		)

		if supplier:
			return supplier


	for serial in serial_numbers:

		supplier = get_supplier_from_serial_document_field(
			serial,
			"purchase_document_no"
		)

		if supplier:
			return supplier


	for serial in serial_numbers:

		supplier = get_supplier_from_serial_document_field(
			serial,
			"creation_document_no"
		)

		if supplier:
			return supplier

	for serial in serial_numbers:

		supplier = get_supplier_from_subcontracting_serial(
			item_code,
			serial
		)

		if supplier:
			return supplier


	for serial in serial_numbers:

		supplier = get_supplier_from_purchase_invoice_serial(
			item_code,
			serial
		)

		if supplier:
			return supplier


	for serial in serial_numbers:

		supplier = get_supplier_from_stock_ledger(
			item_code,
			serial
		)

		if supplier:
			return supplier


	supplier = get_supplier_from_item_supplier(item_code)

	if supplier:
		return supplier

	supplier = get_supplier_from_purchase_history(item_code)

	if supplier:
		return supplier

	return None


def get_supplier_from_purchase_receipt_serial(item_code, serial_no):

	if not serial_no:
		return None

	result = frappe.db.sql(
		"""
		SELECT
			pr.supplier

		FROM
			`tabPurchase Receipt Item` pri

		INNER JOIN
			`tabPurchase Receipt` pr
			ON pr.name = pri.parent

		WHERE
			pr.docstatus = 1
			AND pri.item_code = %(item_code)s

			AND (
				pri.serial_no = %(serial_no)s

				OR FIND_IN_SET(
					%(serial_no)s,

					REPLACE(
						REPLACE(
							pri.serial_no,
							'\\n',
							','
						),
						'\\r',
						''
					)
				) > 0
			)

		ORDER BY
			pr.posting_date ASC

		LIMIT 1
		""",
		{
			"item_code": item_code,
			"serial_no": serial_no,
		},
		as_dict=True,
	)

	if result:
		return result[0].get("supplier")

	return None



def get_supplier_from_serial_document_field(
	serial_no,
	fieldname
):

	if not serial_no:
		return None

	# Check field exists before querying
	if not frappe.db.has_column("Serial No", fieldname):
		return None

	document_no = frappe.db.get_value(
		"Serial No",
		serial_no,
		fieldname
	)

	if not document_no:
		return None

	return get_supplier_from_document_no(document_no)


def get_supplier_from_document_no(document_no):

	if not document_no:
		return None


	if frappe.db.exists("Purchase Receipt", document_no):

		return frappe.db.get_value(
			"Purchase Receipt",
			{
				"name": document_no,
				"docstatus": 1,
			},
			"supplier"
		)

	if frappe.db.exists(
		"Subcontracting Receipt",
		document_no
	):

		return frappe.db.get_value(
			"Subcontracting Receipt",
			{
				"name": document_no,
				"docstatus": 1,
			},
			"supplier"
		)

	if frappe.db.exists(
		"Purchase Invoice",
		document_no
	):

		return frappe.db.get_value(
			"Purchase Invoice",
			{
				"name": document_no,
				"docstatus": 1,
			},
			"supplier"
		)

	if frappe.db.exists(
		"Purchase Order",
		document_no
	):

		return frappe.db.get_value(
			"Purchase Order",
			{
				"name": document_no,
				"docstatus": 1,
			},
			"supplier"
		)


	if frappe.db.exists(
		"Stock Reconciliation",
		document_no
	):

		return get_supplier_from_custom_document(
			"Stock Reconciliation",
			document_no
		)

	
	if frappe.db.exists(
		"Stock Entry",
		document_no
	):

		return get_supplier_from_custom_document(
			"Stock Entry",
			document_no
		)


	if frappe.db.exists(
		"DocType",
		"Opening Stock"
	):

		if frappe.db.exists(
			"Opening Stock",
			document_no
		):

			return get_supplier_from_custom_document(
				"Opening Stock",
				document_no
			)

	return None


def get_supplier_from_custom_document(
	doctype,
	document_no
):

	possible_fields = [
		"supplier",
		"custom_supplier",
		"default_supplier",
	]

	for fieldname in possible_fields:

		if frappe.db.has_column(
			doctype,
			fieldname
		):

			supplier = frappe.db.get_value(
				doctype,
				document_no,
				fieldname
			)

			if supplier:
				return supplier

	return None



def get_supplier_from_subcontracting_serial(
	item_code,
	serial_no
):

	if not serial_no:
		return None

	result = frappe.db.sql(
		"""
		SELECT
			sr.supplier

		FROM
			`tabSubcontracting Receipt Item` sri

		INNER JOIN
			`tabSubcontracting Receipt` sr
			ON sr.name = sri.parent

		WHERE
			sr.docstatus = 1
			AND sri.item_code = %(item_code)s

			AND (
				sri.serial_no = %(serial_no)s

				OR FIND_IN_SET(
					%(serial_no)s,

					REPLACE(
						REPLACE(
							IFNULL(sri.serial_no, ''),
							'\\n',
							','
						),
						'\\r',
						''
					)
				) > 0
			)

		ORDER BY
			sr.posting_date ASC

		LIMIT 1
		""",
		{
			"item_code": item_code,
			"serial_no": serial_no,
		},
		as_dict=True,
	)

	if result:
		return result[0].get("supplier")

	return None


def get_supplier_from_purchase_invoice_serial(
	item_code,
	serial_no
):

	if not serial_no:
		return None

	result = frappe.db.sql(
		"""
		SELECT
			pi.supplier

		FROM
			`tabPurchase Invoice Item` pii

		INNER JOIN
			`tabPurchase Invoice` pi
			ON pi.name = pii.parent

		WHERE
			pi.docstatus = 1
			AND pii.item_code = %(item_code)s

			AND (
				pii.serial_no = %(serial_no)s

				OR FIND_IN_SET(
					%(serial_no)s,

					REPLACE(
						REPLACE(
							IFNULL(pii.serial_no, ''),
							'\\n',
							','
						),
						'\\r',
						''
					)
				) > 0
			)

		ORDER BY
			pi.posting_date ASC

		LIMIT 1
		""",
		{
			"item_code": item_code,
			"serial_no": serial_no,
		},
		as_dict=True,
	)

	if result:
		return result[0].get("supplier")

	return None



def get_supplier_from_stock_ledger(
	item_code,
	serial_no
):

	if not serial_no:
		return None

	entries = frappe.db.sql(
		"""
		SELECT
			voucher_type,
			voucher_no

		FROM
			`tabStock Ledger Entry`

		WHERE
			is_cancelled = 0
			AND item_code = %(item_code)s

			AND (
				serial_no = %(serial_no)s

				OR FIND_IN_SET(
					%(serial_no)s,

					REPLACE(
						REPLACE(
							IFNULL(serial_no, ''),
							'\\n',
							','
						),
						'\\r',
						''
					)
				) > 0
			)

		ORDER BY
			posting_date ASC,
			posting_time ASC

		LIMIT 20
		""",
		{
			"item_code": item_code,
			"serial_no": serial_no,
		},
		as_dict=True,
	)

	for entry in entries:

		voucher_type = entry.get("voucher_type")
		voucher_no = entry.get("voucher_no")

		if not voucher_type or not voucher_no:
			continue

		if voucher_type in [
			"Purchase Receipt",
			"Purchase Invoice",
			"Purchase Order",
			"Subcontracting Receipt",
		]:

			supplier = get_supplier_from_document_no(
				voucher_no
			)

			if supplier:
				return supplier

		if voucher_type in [
			"Stock Reconciliation",
			"Stock Entry",
		]:

			supplier = get_supplier_from_document_no(
				voucher_no
			)

			if supplier:
				return supplier

	return None




def get_supplier_from_item_supplier(item_code):

	if not item_code:
		return None

	result = frappe.db.sql(
		"""
		SELECT
			supplier

		FROM
			`tabItem Supplier`

		WHERE
			parent = %(item_code)s
			AND IFNULL(supplier, '') != ''

		ORDER BY
			idx ASC

		LIMIT 1
		""",
		{
			"item_code": item_code,
		},
		as_dict=True,
	)

	if result:
		return result[0].get("supplier")

	if frappe.db.has_column(
		"Item",
		"default_supplier"
	):

		supplier = frappe.db.get_value(
			"Item",
			item_code,
			"default_supplier"
		)

		if supplier:
			return supplier

	return None



def get_supplier_from_purchase_history(item_code):

	if not item_code:
		return None

	result = frappe.db.sql(
		"""
		SELECT
			pr.supplier

		FROM
			`tabPurchase Receipt Item` pri

		INNER JOIN
			`tabPurchase Receipt` pr
			ON pr.name = pri.parent

		WHERE
			pr.docstatus = 1
			AND pri.item_code = %(item_code)s
			AND IFNULL(pr.supplier, '') != ''

		ORDER BY
			pr.posting_date DESC,
			pr.creation DESC

		LIMIT 1
		""",
		{
			"item_code": item_code,
		},
		as_dict=True,
	)

	if result:
		return result[0].get("supplier")

	return None




def split_serial_numbers(serial_no):

	if not serial_no:
		return []

	if isinstance(serial_no, list):
		return serial_no

	serial_no = str(serial_no)

	serial_no = serial_no.replace(
		"\r",
		"\n"
	)

	serial_no = serial_no.replace(
		",",
		"\n"
	)

	return [
		x.strip()
		for x in serial_no.split("\n")
		if x.strip()
	]




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