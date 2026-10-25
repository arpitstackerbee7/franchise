
import frappe
from frappe import _
from frappe.utils import add_days, getdate, nowdate, now_datetime


def execute(filters=None):
	filters = filters or {}

	validate_filters(filters)

	companies = get_counter_companies(filters)

	if not companies:
		frappe.msgprint(_("No companies found."))
		return [], []

	columns = get_columns()
	data = get_data(filters, companies) or []

	return columns, data



def validate_filters(filters):
	if not filters.get("from_date"):
		frappe.throw(_("From Date is required"))

	if not filters.get("to_date"):
		frappe.throw(_("To Date is required"))

	if getdate(filters.get("from_date")) > getdate(filters.get("to_date")):
		frappe.throw(_("From Date cannot be greater than To Date"))


def get_counter_companies(filters):
	company = filters.get("company")

	company_filters = {}

	if company:
		company_filters["name"] = company

	return frappe.get_all(
		"Company",
		filters=company_filters,
		pluck="name"
	)


# def get_sis_company_map(customer_filter=None):

# 	customer_filters = {
# 		"disabled": 0
# 	}

# 	if customer_filter:
# 		customer_filters["name"] = customer_filter

# 	rows = frappe.get_all(
# 		"Customer",
# 		filters=customer_filters,
# 		fields=["name", "customer_name", "represents_company"]
# 	)

# 	result = {}

# 	for r in rows:

# 		sis_company = r.represents_company or r.customer_name

# 		if frappe.db.exists("Company", sis_company):
# 			result[r.name] = sis_company

# 	return result

def get_sis_company_map(customer_filter=None, customer_group=None):

	customer_filters = {
		"disabled": 0,
		"is_internal_customer": 1
	}

	if customer_filter:
		customer_filters["name"] = customer_filter

	if customer_group:
		customer_filters["customer_group"] = customer_group


	rows = frappe.get_all(
		"Customer",
		filters=customer_filters,
		fields=["name", "customer_name", "represents_company"]
	)

	chosen = {}

	for r in rows:

		sis_company = r.represents_company or r.customer_name

		if not frappe.db.exists("Company", sis_company):
			continue

		# lower number = higher priority
		if r.represents_company:
			priority = 0
		elif r.name == sis_company:
			priority = 1
		else:
			priority = 2

		prev = chosen.get(sis_company)

		if not prev or priority < prev[0]:
			chosen[sis_company] = (priority, r.name)

	return {
		name: company
		for company, (priority, name) in chosen.items()
	}

def get_customer_extra_fields(customers, filters=None):
	if not customers:
		return {}

	filters = filters or {}

	conditions = "c.name IN %(customers)s"

	values = {
		"customers": customers
	}

	if filters.get("agent"):
		conditions += " AND c.custom_agent = %(agent)s"
		values["agent"] = filters.get("agent")

	if filters.get("asm"):
		conditions += " AND c.account_manager = %(asm)s"
		values["asm"] = filters.get("asm")

	rows = frappe.db.sql(
		f"""
		SELECT
			c.name,
			c.custom_agent,
			u.full_name AS asm_name
		FROM `tabCustomer` c
		LEFT JOIN `tabUser` u
			ON u.name = c.account_manager
		WHERE {conditions}
		""",
		values,
		as_dict=True
	)

	return {
		r.name: r
		for r in rows
	}


def get_columns():
	return [

		{
			"label": _("Customer Name"),
			"fieldname": "customer_name",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 130
		},

		{
			"label": _("Agent"),
			"fieldname": "agent",
			"fieldtype": "Data",
			"width": 90
		},

		{
			"label": _("ASM"),
			"fieldname": "asm",
			"fieldtype": "Data",
			"width": 90
		},

		{
			"label": _("Franchise Fees"),
			"fieldname": "net_sale_franchise",
			"fieldtype": "Currency",
			"width": 130
		},

		{
			"label": _("Qty sold at counter"),
			"fieldname": "sale_qty_ytd",
			"fieldtype": "Float",
			"width": 85
		},

		{
			"label": _("Billing Value with gst"),
			"fieldname": "amount_ytd",
			"fieldtype": "Currency",
			"width": 100
		},

		{
			"label": _("Credit Note Value (Disc on Sale)"),
			"fieldname": "credit_note_disc",
			"fieldtype": "Currency",
			"width": 110
		},

		{
			"label": _("Credit Note Value (Any Other)"),
			"fieldname": "credit_note_other",
			"fieldtype": "Currency",
			"width": 110
		},

		{
			"label": _("Debit Note Value (All)"),
			"fieldname": "debit_note",
			"fieldtype": "Currency",
			"width": 85
		},

		{
			"label": _("Collectable amt"),
			"fieldname": "collectable_amount",
			"fieldtype": "Currency",
			"width": 100
		},

		{
			"label": _("Payment received"),
			"fieldname": "payment_received",
			"fieldtype": "Currency",
			"width": 90
		},

		{
			"label": _("Pending Amount"),
			"fieldname": "pending_amount",
			"fieldtype": "Currency",
			"width": 100
		},

		{
			"label": _("Qty"),
			"fieldname": "sale_qty_15",
			"fieldtype": "Float",
			"width": 90
		},

		{
			"label": _("Billing value with gst"),
			"fieldname": "amount_15",
			"fieldtype": "Currency",
			"width": 100
		},

		{
			"label": _("CN Value (Disc on Sale)"),
			"fieldname": "credit_note_disc_15",
			"fieldtype": "Currency",
			"width": 110
		},

		{
			"label": _("CN Value (Any Other)"),
			"fieldname": "credit_note_other_15",
			"fieldtype": "Currency",
			"width": 110
		},



		{
			"label": _("Collectable amount"),
			"fieldname": "collectable_amount_15",
			"fieldtype": "Currency",
			"width": 100
		},

		{
			"label": _("Net Pending"),
			"fieldname": "net_pending",
			"fieldtype": "Currency",
			"width": 100
		}


	]


def get_data(filters, companies):

	from_date = getdate(filters.get("from_date"))
	to_date = getdate(filters.get("to_date"))
	last_15_start = from_date

	customer_filter = filters.get("customer")

	if customer_filter:
		customer_filter = (
			frappe.db.exists("Customer", customer_filter)
			or frappe.db.get_value(
				"Customer",
				{"customer_name": customer_filter, "disabled": 0},
				"name",
				order_by="IFNULL(represents_company, '') = '' asc, creation asc"
			)
			or customer_filter
		)

	sis_map = get_sis_company_map(customer_filter, filters.get("customer_group"))

	sales_values = {
		"companies": companies,
		"from_date": from_date,
		"to_date": to_date,
		"last_15_start": last_15_start,
		"prev_to_date": add_days(from_date, -1)
	}

	customer_condition = ""

	if customer_filter:
		customer_condition = " AND si.customer = %(customer)s"
		sales_values["customer"] = customer_filter


	from erpnext.accounts.report.trial_balance.trial_balance import execute as trial_balance_execute

	tb_to_date = add_days(from_date, -1)

	opening_map = {}

	for customer, sis_company in sis_map.items():

		fiscal_year = frappe.db.get_value(
			"Fiscal Year",
			{
				"year_start_date": ["<=", tb_to_date],
				"year_end_date": [">=", tb_to_date],
				"disabled": 0
			},
			["name", "year_start_date", "year_end_date"],
			as_dict=True
		)

		if not fiscal_year:
			frappe.throw(
				_("No active Fiscal Year found for {0}").format(tb_to_date)
			)

		tb_filters = frappe._dict({
			"company": sis_company,
			"fiscal_year": fiscal_year.name,
			"from_date": fiscal_year.year_start_date,
			"to_date": tb_to_date,
			"with_period_closing_entry_for_opening": 1,
			"with_period_closing_entry_for_current": 1,
			"show_net_values": 1,
			"show_group_accounts": 1,
			"include_default_book_entries": 1,
		})

		columns, trial_balance_data = trial_balance_execute(tb_filters)

		closing_dr = 0

		for row in trial_balance_data:
			if row.get("account_name") == "Stock Expenses":
				closing_dr = row.get("closing_debit") or 0
				break

		opening_map[customer] = frappe._dict({
			"opening_stock": closing_dr
		})

	# =====================================================
	# SALE QUANTITY




	#from franchise_erp.franchise_erp.doctype.sis_debit_note_log.sis_debit_note_log import fetch_invoices
	from franchise_erp.franchise_erp.doctype.sis_debit_note_log.sis_debit_note_log import get_item_input_gst

	from decimal import Decimal, ROUND_HALF_UP


	def R2(val):
		return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


	@frappe.whitelist()
	def fetch_invoices(company, from_date=None, to_date=None):

		import frappe
		from decimal import Decimal
		from frappe.utils import getdate


		# -------------------------------------------------------------------
		# SMALL HELPER → ALWAYS RETURN DECIMAL
		# -------------------------------------------------------------------

		def D(val):
			return Decimal(str(val or 0))


		# -------------------------------------------------------------------
		# FETCH CONFIG VALUES
		# -------------------------------------------------------------------

		config = frappe.db.get_value(
			"SIS Configuration",
			{"company": company},
			[
				"fresh_margin",
				"discounted_margin",
				"sis_debit_note_creation_period",
				"auto_credit_note_percent",
				"discount_threshold",
				"output_gst_min_net_rate",
				"input_gst_for_opening_stock"
			],
			as_dict=True
		)

		if not config or not config.sis_debit_note_creation_period:
			frappe.throw("Please set Debit Note Creation Period in SIS Configuration")

		fresh_margin = D(config.fresh_margin)
		discounted_margin = D(config.discounted_margin)
		period_type = config.sis_debit_note_creation_period
		auto_credit_note_percent = D(config.auto_credit_note_percent)
		discount_threshold = D(config.discount_threshold)
		output_gst_min_net_rate = D(config.output_gst_min_net_rate)
		input_gst_for_opening_stock = D(config.input_gst_for_opening_stock)


		# -------------------------------------------------------------------
		# CLEAN DATE INPUTS
		# -------------------------------------------------------------------

		from_date = None if not from_date or from_date in ["", "null"] else from_date
		to_date = None if not to_date or to_date in ["", "null"] else to_date


		# 🔥 If frontend sent dates → ALWAYS use them
		if from_date and to_date:
			pass

		# fallback to config (only if frontend empty)
		elif period_type == "Date Range":
			from_date, to_date = frappe.db.get_value(
				"SIS Configuration",
				{"company": company},
				["from_date", "to_date"]
			)

		# fallback to period type
		else:
			from_date, to_date = get_period_dates(period_type)

		if not from_date or not to_date:
			frappe.throw("Please select From Date and To Date")

		from_date = getdate(from_date)
		to_date = getdate(to_date)

		if from_date > to_date:
			frappe.throw("From Date cannot be greater than To Date")


		# -------------------------------------------------------------------
		# FETCH DELIVERY NOTE DATA
		# -------------------------------------------------------------------

		invoices = frappe.db.sql("""
			SELECT
				dn.name AS name,
				dn.posting_date,
				dn.posting_time,
				dn.customer,
				dn.is_return,              -- ✅ CORRECT
				dni.name AS sii_name,
				dni.item_code,
				dni.item_name,
				dni.serial_no,
				dni.qty,
				dni.rate,
				dni.price_list_rate,
				dni.discount_percentage,
				dni.custom_is_promo_scheme,
				dni.custom_promo_discount_percent,
				(dni.qty * dni.price_list_rate) AS total_amount
			FROM `tabDelivery Note` dn
			JOIN `tabDelivery Note Item` dni ON dni.parent = dn.name
			WHERE
				dn.company = %s
				AND dn.posting_date BETWEEN %s AND %s
				AND dn.docstatus = 1
			ORDER BY dn.posting_date DESC, dn.posting_time DESC, dn.name, dni.idx
		""", (company, from_date, to_date), as_dict=True)

		processed = []


		# -------------------------------------------------------------------
		# PROCESS EACH ITEM
		# -------------------------------------------------------------------

		for r in invoices:

			total_amount = D(r.total_amount)

			discount_percentage = D(r.discount_percentage)
			promo_discount = D(r.custom_promo_discount_percent)
			is_promo = r.custom_is_promo_scheme

			#  PROMO DISCOUNT OVERRIDE
			if is_promo and promo_discount > 0:
				discount_percentage = promo_discount

			discount_amount = (total_amount * discount_percentage) / D(100)
			net_amount = total_amount - discount_amount


			# -------------------------------------------------------------------
			# OUTPUT GST
			# -------------------------------------------------------------------

			# gst_percent = D(5) if net_amount <= D(2500) else D(18)
			# out_put_gst_value = net_amount * gst_percent / (D(100) + gst_percent)
			# out_put_gst_value = R2(out_put_gst_value)
			# net_sale_value = net_amount - out_put_gst_value

			# gst_percent = D(5) if net_amount <= output_gst_min_net_rate else D(18)
			# out_put_gst_value = net_amount * gst_percent / (D(100) + gst_percent)
			# out_put_gst_value = R2(out_put_gst_value)
			# net_sale_value = net_amount - out_put_gst_value

			# -------------------------------
			# OUTPUT GST (FINAL FIX)
			# -------------------------------

			is_return = r.is_return or 0

			#  IMPORTANT: use absolute value for GST decision
			check_amount = abs(net_amount)

			if is_return == 1:
				if check_amount > output_gst_min_net_rate:
					gst_percent = D(18)
				else:
					gst_percent = D(5)
			else:
				gst_percent = D(5) if check_amount <= output_gst_min_net_rate else D(18)

			# GST calculation (original net_amount use karo, sign same rahega)
			out_put_gst_value = net_amount * gst_percent / (D(100) + gst_percent)
			out_put_gst_value = R2(out_put_gst_value)

			net_sale_value = net_amount - out_put_gst_value


			# -------------------------------------------------------------------
			# MARGIN LOGIC
			# -------------------------------------------------------------------

			# if is_promo or discount_percentage > 0:
			#     margin_percent = discounted_margin
			# else:
			#     margin_percent = fresh_margin

			if is_promo and promo_discount > 0:
				# Promo scheme with actual promo discount → discounted margin
				margin_percent = discounted_margin
			elif not is_promo and discount_percentage > 0:
				# Normal discount → discounted margin
				margin_percent = discounted_margin
			else:
				# Promo scheme with 0 promo discount OR no discount → fresh margin
				margin_percent = fresh_margin

			margin_amount = (net_amount * margin_percent) / D(100)
			inv_base_value = net_sale_value - margin_amount
			inv_base_value = R2(inv_base_value)


			# -------------------------------------------------------------------
			# INPUT GST
			# -------------------------------------------------------------------

			st_percent, gst_amount_per_item, single_item_rate = get_item_input_gst(
				r.item_code, company
			)


			# -------------------------------------------------------------------
			# CONDITION: Only when GST is 0
			# -------------------------------------------------------------------

			if gst_amount_per_item == 0:

				# STEP 1: MRP
				mrp1 = D(r.price_list_rate or 0)

				# STEP 2: OUTPUT GST %
				if abs(mrp1) <= output_gst_min_net_rate:
					output_gst_percent1 = D(5)
				else:
					output_gst_percent1 = D(18)

				# STEP 3: OUTPUT GST VALUE (INCLUSIVE)
				output_gst_value1 = (mrp1 * output_gst_percent1) / (D(100) + output_gst_percent1)
				output_gst_value1 = R2(output_gst_value1)

				# NET SALE
				net_sale_value1 = mrp1 - output_gst_value1
				net_sale_value1 = R2(net_sale_value1)

				# STEP 4: MARGIN
				margin_amount1 = (mrp1 * fresh_margin) / D(100)
				margin_amount1 = R2(margin_amount1)

				# STEP 5: INVENTORY BASE VALUE
				inv_base_value1 = net_sale_value1 - margin_amount1
				inv_base_value1 = R2(inv_base_value1)

				# STEP 6: INPUT GST %
				if abs(inv_base_value1) <= input_gst_for_opening_stock:
					st_percent1 = D(5)
				else:
					st_percent1 = D(18)

				# STEP 7: INPUT GST VALUE (EXCLUSIVE) ✅ IMPORTANT
				input_gst1 = (inv_base_value1 * st_percent1) / D(100)
				input_gst1 = R2(input_gst1)

				# STEP 8: FINAL
				invoice_value1 = inv_base_value1 + input_gst1
				invoice_value1 = R2(invoice_value1)

				# print("MRP:", mrp1)

				# print("Output GST %:", output_gst_percent1)

				# print("Output GST Value:", output_gst_value1)

				# print("Net Sale Value:", net_sale_value1)

				# print("Margin %:", fresh_margin)
				# print("Margin Value:", margin_amount1)

				# print("Inventory Base Value:", inv_base_value1)

				# print("Input GST %:", st_percent1)

				# print("Input GST Value:", input_gst1)

				# print("Final Invoice Value:", invoice_value1)

				gst_amount_per_item = D(input_gst1)
				single_item_rate = D(invoice_value1)
				total_serial_invoice_value = single_item_rate + gst_amount_per_item
				invoice_value1 = inv_base_value + gst_amount_per_item

				if discount_percentage == 0:
					debit_note_value = 0
				else:
					debit_note_value = single_item_rate - invoice_value1

				# Return case → GST negative
				is_return = r.is_return or 0   # 0 or 1

				if is_return == 1:
					gst_amount_per_item1 = -gst_amount_per_item
					single_item_rate1 = -single_item_rate
					invoice_value1 = inv_base_value + gst_amount_per_item1

					if discount_percentage == 0:
						debit_note_value = 0
					else:
						debit_note_value = single_item_rate1 - (invoice_value1)

					# print("0:", gst_amount_per_item1)


			else:
				gst_amount_per_item = D(gst_amount_per_item)
				single_item_rate = D(single_item_rate)
				total_serial_invoice_value = single_item_rate + gst_amount_per_item
				invoice_value1 = inv_base_value + gst_amount_per_item

				if discount_percentage == 0:
					debit_note_value = 0
				else:
					debit_note_value = total_serial_invoice_value - invoice_value1

				# Return case → GST negative
				is_return = r.is_return or 0   # 0 or 1

				if is_return == 1:
					gst_amount_per_item1 = -gst_amount_per_item
					single_item_rate1 = -single_item_rate
					invoice_value1 = inv_base_value + gst_amount_per_item1
					debit_note_value1 = single_item_rate1 - (invoice_value1)

					if discount_percentage == 0:
						debit_note_value = 0
					else:
						debit_note_value = debit_note_value1 + (gst_amount_per_item1)

					# print("0:", gst_amount_per_item1)


			#    total_serial_invoice_value = single_item_rate1 + gst_amount_per_item1
			#    invoice_value1 = inv_base_value + gst_amount_per_item1
			#    if discount_percentage == 0:
			#         debit_note_value = 0
			#    else:
			#         debit_note_value = invoice_value1 - total_serial_invoice_value


			if is_return == 1:
				gst_amount_per_item_1 = -gst_amount_per_item
			else:
				gst_amount_per_item_1 = gst_amount_per_item


			# -------------------------------------------------------------------
			# FINAL UPDATE
			# -------------------------------------------------------------------

			r.update({
				"total_amount": float(total_amount),
				"discount_percentage": float(discount_percentage),
				"discount_amount": float(discount_amount),
				"net_amount": float(net_amount),
				"gst_percent": float(gst_percent),
				"gst_amount": float(out_put_gst_value),
				"net_sale_value": float(net_sale_value),
				"margin_percent": float(margin_percent),
				"margin_amount": float(margin_amount),
				"inv_base_value": float(inv_base_value),
				"in_put_gst_value": float(gst_amount_per_item_1),
				"invoice_value": float(invoice_value1),
				"debit_note": float(debit_note_value),
				"serial_no": r.serial_no or ""
			})

			processed.append(r)


		# -------------------------------------------------------------------
		# RETURN
		# -------------------------------------------------------------------

		return {
			"invoice_list": processed,
			"period_type": period_type,
			"from_date": str(from_date),
			"to_date": str(to_date),
		}


	# ======================================================
	#       PERIOD DATE CALCULATION LOGIC
	# ======================================================

	def get_period_dates(period_type):
		today = getdate(nowdate())
		import calendar


		# WEEKLY -- Monday to Sunday
		if period_type == "Weekly":
			weekday = today.weekday()
			start = add_days(today, -weekday)
			end = add_days(start, 6)
			return start, end


		# FORTNIGHTLY
		elif period_type == "Fortnightly":
			first_day = today.replace(day=1)
			last_day = today.replace(day=calendar.monthrange(today.year, today.month)[1])

			if today.day <= 15:
				return first_day, first_day.replace(day=15)
			else:
				return first_day.replace(day=16), last_day


		# MONTHLY
		elif period_type == "Monthly":
			first_day = today.replace(day=1)
			last_day = today.replace(day=calendar.monthrange(today.year, today.month)[1])
			return first_day, last_day

		return today, today

	qty_map = {}
	first_delivery_data = frappe.db.sql(
		"""
		SELECT
			dn.company AS customer,
			MIN(dn.posting_date) AS first_date
		FROM `tabDelivery Note` dn
		WHERE
			dn.docstatus = 1
		GROUP BY dn.company
		""",
		as_dict=True
	)
	first_delivery_map = {
    (d.customer or "").strip().lower(): d.first_date
    for d in first_delivery_data
    }

	# -----------------------------------------------------
	# Customer rows ke liye
	# -----------------------------------------------------

	for customer, sis_company in sis_map.items():

		qty_map[customer] = {
			"qty_ytd": 0,
			"qty_15": 0,
			"amount_ytd": 0,
			"amount_15": 0
		}

		# -------------------------------------------------
		# PREVIOUS PERIOD
		# -------------------------------------------------

		first_delivery_date = first_delivery_map.get((sis_company or "").strip().lower())
		previous_period_end = add_days(from_date, -1)

		if first_delivery_date and getdate(first_delivery_date) <= previous_period_end:
			previous_result = fetch_invoices(
				company=sis_company,
				from_date=str(first_delivery_date),
				to_date=str(previous_period_end)
			)
		else:
			previous_result = {}

		for row in (previous_result.get("invoice_list") or []):
			qty_map[customer]["qty_ytd"] += float(row.get("qty") or 0)
			qty_map[customer]["amount_ytd"] += (
				float(row.get("inv_base_value") or 0)
				+ float(row.get("in_put_gst_value") or 0)
				+ float(row.get("debit_note") or 0)
			)


		# -------------------------------------------------
		# LAST 15 DAYS
		# -------------------------------------------------

		last_15_result = fetch_invoices(
			company=sis_company,
			from_date=str(last_15_start),
			to_date=str(to_date)
		)

		for row in (last_15_result.get("invoice_list") or []):
			qty_map[customer]["qty_15"] += float(row.get("qty") or 0)
			qty_map[customer]["amount_15"] += (
				float(row.get("inv_base_value") or 0)
				+ float(row.get("in_put_gst_value") or 0)
				+ float(row.get("debit_note") or 0)
			)


	# =====================================================
	# NET SALE UNDER FRANCHISE FEES
	# Sales Invoice Item where item_code = 'Franchise Services'
	# Cumulative since inception till "today" (system date when
	# report is run) - NOT bound by the from_date/to_date filters.
	# =====================================================

	franchise_customer_condition = ""

	franchise_values = {
		"companies": companies,
		"now": now_datetime()
	}

	if customer_filter:
		franchise_customer_condition = " AND si.customer = %(customer)s"
		franchise_values["customer"] = customer_filter

	franchise_data = frappe.db.sql(
		f"""
		SELECT
			si.customer AS customer,
			SUM(
				ROUND(
					sii.net_amount + IFNULL(
						(
							SELECT SUM(
								CAST(
									JSON_UNQUOTE(
										JSON_EXTRACT(stc.item_wise_tax_detail, CONCAT('$."', sii.item_code, '"[1]'))
									) AS DECIMAL(18,2)
								)
							)
							FROM `tabSales Taxes and Charges` stc
							WHERE stc.parent = si.name
								AND stc.account_head LIKE 'Output Tax%%'
						),
						0
					)
				)
			) AS net_sale_franchise

		FROM `tabSales Invoice Item` sii

		INNER JOIN `tabSales Invoice` si
			ON si.name = sii.parent

		WHERE
			si.docstatus = 1
			AND si.company IN %(companies)s
			AND si.creation <= %(now)s
			AND sii.item_code = 'Franchise Services'
			{franchise_customer_condition}

		GROUP BY si.customer
		""",
		franchise_values,
		as_dict=True
	)

	franchise_map = {
		d.customer: d
		for d in franchise_data
	}


	# =====================================================
	# CREDIT NOTE / DEBIT NOTE
	# From General Ledger, Voucher Type = Journal Entry only
	# Previous period: first delivery date (by company) -> from_date - 1
	# Last 15 Days: last_15_start -> to_date
	# =====================================================

	# journal_note_customer_condition = ""

	# if customer_filter:
	# 	journal_note_customer_condition = " AND gle.party = %(customer)s"

	# journal_note_data = frappe.db.sql(
	# 	f"""
	# 	SELECT
	# 		gle.party AS customer,

	# 		SUM(
	# 			CASE
	# 				WHEN gle.posting_date <= %(prev_to_date)s
	# 					AND gle.voucher_subtype IN ('Credit Note', 'Journal Entry')
	# 				THEN gle.credit
	# 				ELSE 0
	# 			END
	# 		) AS credit_note,

	# 		SUM(
	# 			CASE
	# 				WHEN gle.posting_date >= %(last_15_start)s
	# 					AND gle.posting_date <= %(to_date)s
	# 					AND gle.voucher_subtype IN ('Credit Note', 'Journal Entry')
	# 				THEN gle.credit
	# 				ELSE 0
	# 			END
	# 		) AS credit_note_15,

	# 		SUM(
	# 			CASE
	# 				WHEN gle.posting_date <= %(prev_to_date)s
	# 					AND gle.voucher_subtype IN ('Debit Note', 'Journal Entry')
	# 				THEN gle.debit
	# 				ELSE 0
	# 			END
	# 		) AS debit_note,

	# 		SUM(
	# 			CASE
	# 				WHEN gle.posting_date >= %(last_15_start)s
	# 					AND gle.posting_date <= %(to_date)s
	# 					AND gle.voucher_subtype IN ('Debit Note', 'Journal Entry')
	# 				THEN gle.debit
	# 				ELSE 0
	# 			END
	# 		) AS debit_note_15

	# 	FROM `tabGL Entry` gle

	# 	WHERE
	# 		gle.is_cancelled = 0
	# 		AND gle.company IN %(companies)s
	# 		AND gle.posting_date <= %(to_date)s
	# 		AND gle.party_type = 'Customer'
	# 		AND IFNULL(gle.party, '') != ''
	# 		AND gle.voucher_type = 'Journal Entry'
	# 		AND gle.voucher_subtype IN ('Credit Note', 'Debit Note', 'Journal Entry')
	# 		{journal_note_customer_condition}

	# 	GROUP BY gle.party
	# 	""",
	# 	sales_values,
	# 	as_dict=True
	# )

	# journal_note_map = {
	# 	d.customer: d
	# 	for d in journal_note_data
	# }

	journal_note_customer_condition = ""

	if customer_filter:
		journal_note_customer_condition = " AND gle.party = %(customer)s"

	journal_note_data = []   

	journal_note_data = frappe.db.sql(
		f"""
		SELECT
			gle.party AS customer,

			SUM(CASE
				WHEN gle.posting_date <= %(prev_to_date)s
					AND gle.voucher_subtype IN ('Credit Note', 'Journal Entry')
					AND gle.against LIKE '%%DISCOUNT ON SALE - TZUPL%%'
				THEN gle.credit ELSE 0 END) AS credit_note_disc,

			SUM(CASE
				WHEN gle.posting_date <= %(prev_to_date)s
					AND gle.voucher_subtype IN ('Credit Note', 'Journal Entry')
					AND IFNULL(gle.against, '') NOT LIKE '%%DISCOUNT ON SALE - TZUPL%%'
				THEN gle.credit ELSE 0 END) AS credit_note_other,

			SUM(CASE
				WHEN gle.posting_date >= %(last_15_start)s
					AND gle.posting_date <= %(to_date)s
					AND gle.voucher_subtype IN ('Credit Note', 'Journal Entry')
					AND gle.against LIKE '%%DISCOUNT ON SALE - TZUPL%%'
				THEN gle.credit ELSE 0 END) AS credit_note_disc_15,

			SUM(CASE
				WHEN gle.posting_date >= %(last_15_start)s
					AND gle.posting_date <= %(to_date)s
					AND gle.voucher_subtype IN ('Credit Note', 'Journal Entry')
					AND IFNULL(gle.against, '') NOT LIKE '%%DISCOUNT ON SALE - TZUPL%%'
				THEN gle.credit ELSE 0 END) AS credit_note_other_15,

			SUM(CASE
				WHEN gle.posting_date <= %(prev_to_date)s
					AND gle.voucher_subtype IN ('Debit Note', 'Journal Entry')
				THEN gle.debit ELSE 0 END) AS debit_note

			

		FROM `tabGL Entry` gle
		WHERE
			gle.is_cancelled = 0
			AND gle.company IN %(companies)s
			AND gle.posting_date <= %(to_date)s
			AND gle.party_type = 'Customer'
			AND IFNULL(gle.party, '') != ''
			AND gle.voucher_type = 'Journal Entry'
			AND gle.voucher_subtype IN ('Credit Note', 'Debit Note', 'Journal Entry')
			{journal_note_customer_condition}
		GROUP BY gle.party
		""",
		sales_values,
		as_dict=True
	)

	journal_note_map = {
		d.customer: d
		for d in journal_note_data
	}

	# =====================================================
	# PAYMENT / COLLECTION
	# =====================================================

	payment_values = {
		"companies": companies,
		"from_date": from_date,
		"to_date": to_date,
		"last_15_start": last_15_start
	}

	payment_customer_condition = ""

	if customer_filter:
		payment_customer_condition = " AND pe.party = %(customer)s"
		payment_values["customer"] = customer_filter


	payment_data = frappe.db.sql(
		f"""
		SELECT
			pe.party AS customer,

			SUM(
				CASE
					WHEN pe.posting_date < %(last_15_start)s
					THEN pe.paid_amount
					ELSE 0
				END
			) AS previous_collection_amount,

			SUM(
				CASE
					WHEN pe.posting_date >= %(last_15_start)s
					THEN pe.paid_amount
					ELSE 0
				END
			) AS collection_15

		FROM `tabPayment Entry` pe

		WHERE
			pe.docstatus = 1
			AND pe.payment_type = 'Receive'
			AND pe.party_type = 'Customer'
			AND pe.company IN %(companies)s
			AND pe.posting_date >= %(from_date)s
			AND pe.posting_date <= %(to_date)s
			{payment_customer_condition}

		GROUP BY pe.party
		""",
		payment_values,
		as_dict=True
	)

	payment_map = {
		d.customer: d
		for d in payment_data
	}

	# =====================================================
	# PAYMENT RECEIVED (Cumulative till exact date+time when
	# report is run, using Payment Entry's creation timestamp
	# as cutoff - NOT bound by from_date/to_date filters)
	# =====================================================

	payment_received_customer_condition = ""

	payment_received_values = {
		"companies": companies
	}

	if customer_filter:
		payment_received_customer_condition = " AND gle.party = %(customer)s"
		payment_received_values["customer"] = customer_filter

	payment_received_data = frappe.db.sql(
		f"""
		SELECT
			gle.party AS customer,

			SUM(
				CASE
					WHEN gle.voucher_subtype = 'Receive'
					THEN gle.credit
					ELSE 0
				END
			) AS payment_receive,

			SUM(
				CASE
					WHEN gle.voucher_subtype = 'Pay'
					THEN gle.debit
					ELSE 0
				END
			) AS payment_pay,

			SUM(
				CASE
					WHEN gle.voucher_subtype = 'Receive'
					THEN gle.credit
					WHEN gle.voucher_subtype = 'Pay'
					THEN -gle.debit
					ELSE 0
				END
			) AS payment_received

		FROM `tabGL Entry` gle

		WHERE
			gle.is_cancelled = 0
			AND gle.company IN %(companies)s
			AND gle.party_type = 'Customer'
			AND IFNULL(gle.party, '') != ''
			AND gle.voucher_type = 'Payment Entry'
			AND gle.voucher_subtype IN ('Receive', 'Pay')
			{payment_received_customer_condition}

		GROUP BY gle.party
		""",
		payment_received_values,
		as_dict=True
	)

	payment_received_map = {
		d.customer: d
		for d in payment_received_data
	}

	# =====================================================
	# ALL CUSTOMERS
	# =====================================================

	# customers = sorted(
	# 	set(
	# 		list(opening_map)
	# 		+ list(qty_map)
	# 		+ list(franchise_map)
	# 		+ list(journal_note_map)
	# 		+ list(payment_map)
	# 		+ list(payment_received_map)
	# 	)
	# )
	# if filters.get("customer_group"):
	# 	group_customers = set(
	# 		frappe.get_all(
	# 			"Customer",
	# 			filters={
	# 				"customer_group": filters.get("customer_group"),
	# 				"disabled": 0
	# 			},
	# 			pluck="name"
	# 		)
	# 	)

	# 	customers = [c for c in customers if c in group_customers]

	# if not customers:
	# 	return []
	customers = sorted(sis_map.keys())

	if not customers:
		return []


	# =====================================================
	# AGENT AND ASM FILTERING
	# =====================================================

	customer_map = get_customer_extra_fields(
		customers,
		filters
	)

	if filters.get("agent") or filters.get("asm"):

		customers = [
			customer
			for customer in customers
			if customer in customer_map
		]


	# =====================================================
	# FINAL DATA
	# =====================================================

	data = []

	for customer in customers:

		cust = customer_map.get(
			customer,
			frappe._dict()
		)

		opening = opening_map.get(
			customer,
			frappe._dict()
		)
		qty = qty_map.get(
			customer,
			frappe._dict()
		)

		franchise = franchise_map.get(
			customer,
			frappe._dict()
		)



		journal_note = journal_note_map.get(
			customer,
			frappe._dict()
		)

		payment = payment_map.get(
			customer,
			frappe._dict()
		)


		opening_stock = opening.get("opening_stock") or 0

		net_sale_franchise = franchise.get("net_sale_franchise") or 0

		sale_qty_ytd = qty.get("qty_ytd") or 0
		sale_qty_15 = qty.get("qty_15") or 0

		amount_ytd = qty.get("amount_ytd") or 0
		amount_15 = qty.get("amount_15") or 0

		credit_note_disc = -(journal_note.get("credit_note_disc") or 0)
		credit_note_other = -(journal_note.get("credit_note_other") or 0)

		credit_note_disc_15 = -(journal_note.get("credit_note_disc_15") or 0)
		credit_note_other_15 = -(journal_note.get("credit_note_other_15") or 0)

		debit_note = journal_note.get("debit_note") or 0

		previous_collection_amount = (
			payment.get("previous_collection_amount") or 0
		)

		collection_15 = (
			payment.get("collection_15") or 0
		)


		payment_rec = payment_received_map.get(
			customer,
			frappe._dict()
		)

		payment_received = payment_rec.get("payment_received") or 0



		collectable_amount = (
			net_sale_franchise
			+ amount_ytd
			+ credit_note_disc
			+ credit_note_other
			+ debit_note
		)


		collectable_amount_15 = (
			amount_15
			+ credit_note_disc_15
			+ credit_note_other_15
		)



		pending_amount = collectable_amount - payment_received

		net_pending = pending_amount + collectable_amount_15

		data.append({
			"customer_name": customer,
			"agent": cust.get("custom_agent"),
			"asm": cust.get("asm_name"),

			"net_sale_franchise": net_sale_franchise,

			"sale_qty_ytd": sale_qty_ytd,
			"amount_ytd": amount_ytd,

			"credit_note_disc": credit_note_disc,
			"credit_note_other": credit_note_other,
			
			"debit_note": debit_note,

			"payment_received": payment_received,
			"collectable_amount": collectable_amount,
			"pending_amount": pending_amount,

			"sale_qty_15": sale_qty_15,
			"amount_15": amount_15,

			"credit_note_disc_15": credit_note_disc_15,
			"credit_note_other_15": credit_note_other_15,


			"collectable_amount_15": collectable_amount_15,

			"net_pending": net_pending

			
		})


	return data

# @frappe.whitelist()
# @frappe.validate_and_sanitize_search_inputs
# def customer_query(doctype, txt, searchfield, start, page_len, filters):
# 	return frappe.db.sql(
# 		"""
# 		SELECT name, customer_name
# 		FROM `tabCustomer`
# 		WHERE disabled = 0
# 			AND (
# 				name LIKE %(txt)s
# 				OR customer_name LIKE %(txt)s
# 			)
# 		ORDER BY
# 			CASE WHEN customer_name LIKE %(start_txt)s THEN 0 ELSE 1 END,
# 			customer_name
# 		LIMIT %(start)s, %(page_len)s
# 		""",
# 		{
# 			"txt": f"%{txt}%",
# 			"start_txt": f"{txt}%",
# 			"start": start,
# 			"page_len": page_len
# 		}
# 	)
@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def customer_query(doctype, txt, searchfield, start, page_len, filters):
	conditions = ""
	values = {
		"txt": f"%{txt}%",
		"start_txt": f"{txt}%",
		"start": start,
		"page_len": page_len
	}

	if isinstance(filters, str):
		filters = frappe.parse_json(filters)

	if filters and filters.get("customer_group"):
		conditions = " AND customer_group = %(customer_group)s"
		values["customer_group"] = filters.get("customer_group")

	return frappe.db.sql(
		f"""
		SELECT name, customer_name
		FROM `tabCustomer`
		WHERE disabled = 0
			AND (
				name LIKE %(txt)s
				OR customer_name LIKE %(txt)s
			)
			{conditions}
		ORDER BY
			CASE WHEN customer_name LIKE %(start_txt)s THEN 0 ELSE 1 END,
			customer_name
		LIMIT %(start)s, %(page_len)s
		""",
		values
	)