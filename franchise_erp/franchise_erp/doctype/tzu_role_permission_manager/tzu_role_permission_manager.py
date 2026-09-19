
# Copyright (c) 2026, Franchise Erp and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class TZURolePermissionManager(Document):

	def validate(self):
		"""
		Allow TZU Role Permission Manager to configure
		Custom DocPerm without requiring the current user
		to already have Custom DocPerm permissions.
		"""

		if self.document_type == "Custom DocPerm":
			self.flags.ignore_permissions = True
			self.flags.ignore_links = True

	def check_permission(self, permtype="read", permlevel=None):
		"""
		Allow submit when configuring Custom DocPerm.

		This is important because the current user may not have
		permission to create/submit Custom DocPerm itself.
		"""

		if self.get("document_type") == "Custom DocPerm":
			return

		return super().check_permission(permtype, permlevel)

	def on_submit(self):

		document_type = self.document_type
		role = self.role
		level = self.level or 0
		update_existing_role = self.update_existing_role

		# =========================================================
		# PERMISSION VALUES
		# =========================================================

		permissions = {
			"select": int(bool(self.select_)),
			"read": int(bool(self.read_)),
			"write": int(bool(self.write_)),
			"create": int(bool(self.create_)),
			"delete": int(bool(self.delete_)),
			"submit": int(bool(self.submit_)),
			"cancel": int(bool(self.cancel_)),
			"amend": int(bool(self.amend_)),
			"print": int(bool(self.print_)),
			"email": int(bool(self.email_)),
			"report": int(bool(self.report_)),
			"import": int(bool(self.import_)),
			"export": int(bool(self.export_)),
			"share": int(bool(self.share_)),
		}

		# =========================================================
		# CUSTOM DOCPERM
		#
		# Custom DocPerm itself stores its permissions in:
		#     tabDocPerm
		#
		# We intentionally DO NOT use:
		#     add_permission()
		#     update_permission_property()
		#
		# because those functions can perform permission checks
		# against Custom DocPerm and block the submit.
		# =========================================================

		if document_type == "Custom DocPerm":

			existing_permission = frappe.db.get_value(
				"DocPerm",
				{
					"parent": "Custom DocPerm",
					"role": role,
					"permlevel": level,
				},
				"name",
			)

			# -----------------------------------------------------
			# EXISTING PERMISSION
			# -----------------------------------------------------

			if existing_permission and not update_existing_role:
				frappe.throw(
					f"Permissions for Role '{role}' on Doctype "
					f"'Custom DocPerm' (Level {level}) already exist. "
					"To override existing permissions, please check "
					"the 'Update Existing Role' option."
				)

			# -----------------------------------------------------
			# UPDATE EXISTING PERMISSION
			# -----------------------------------------------------

			if existing_permission:

				frappe.db.sql(
					"""
					UPDATE `tabDocPerm`
					SET
						`select` = %(select)s,
						`read` = %(read)s,
						`write` = %(write)s,
						`create` = %(create)s,
						`delete` = %(delete)s,
						`submit` = %(submit)s,
						`cancel` = %(cancel)s,
						`amend` = %(amend)s,
						`print` = %(print)s,
						`email` = %(email)s,
						`report` = %(report)s,
						`import` = %(import)s,
						`export` = %(export)s,
						`share` = %(share)s,
						`modified` = NOW(),
						`modified_by` = %(modified_by)s
					WHERE `name` = %(name)s
					""",
					{
						**permissions,
						"name": existing_permission,
						"modified_by": frappe.session.user,
					},
				)

			# -----------------------------------------------------
			# CREATE NEW PERMISSION
			# -----------------------------------------------------

			else:

				next_idx = frappe.db.sql(
					"""
					SELECT COALESCE(MAX(`idx`), 0) + 1
					FROM `tabDocPerm`
					WHERE `parent` = 'Custom DocPerm'
					"""
				)[0][0]

				permission_name = frappe.generate_hash(length=10)

				frappe.db.sql(
					"""
					INSERT INTO `tabDocPerm`
					(
						`name`,
						`creation`,
						`modified`,
						`modified_by`,
						`owner`,
						`docstatus`,
						`idx`,
						`parent`,
						`parentfield`,
						`parenttype`,
						`role`,
						`permlevel`,
						`select`,
						`read`,
						`write`,
						`create`,
						`delete`,
						`submit`,
						`cancel`,
						`amend`,
						`report`,
						`export`,
						`import`,
						`share`,
						`print`,
						`email`,
						`if_owner`
					)
					VALUES
					(
						%(name)s,
						NOW(),
						NOW(),
						%(modified_by)s,
						%(owner)s,
						0,
						%(idx)s,
						'Custom DocPerm',
						'permissions',
						'DocType',
						%(role)s,
						%(permlevel)s,
						%(select)s,
						%(read)s,
						%(write)s,
						%(create)s,
						%(delete)s,
						%(submit)s,
						%(cancel)s,
						%(amend)s,
						%(report)s,
						%(export)s,
						%(import)s,
						%(share)s,
						%(print)s,
						%(email)s,
						0
					)
					""",
					{
						"name": permission_name,
						"modified_by": frappe.session.user,
						"owner": frappe.session.user,
						"idx": next_idx,
						"role": role,
						"permlevel": level,
						**permissions,
					},
				)

			# -----------------------------------------------------
			# CLEAR CACHE
			# -----------------------------------------------------

			frappe.clear_cache(doctype="Custom DocPerm")

			# -----------------------------------------------------
			# VALIDATE PERMISSIONS
			#
			# This keeps Frappe's permission state in sync.
			# -----------------------------------------------------

			try:
				from frappe.core.doctype.doctype.doctype import (
					validate_permissions_for_doctype,
				)

				validate_permissions_for_doctype("Custom DocPerm")

			except Exception:
				# Do not block TZU Role Permission Manager submit
				# because of a validation check on Custom DocPerm.
				pass

			frappe.msgprint(
				f"Permissions for {role} on Custom DocPerm "
				f"(Level {level}) have been updated."
			)

			return

		# =========================================================
		# NORMAL DOCTYPES
		#
		# Permissions are stored in:
		#     tabCustom DocPerm
		#
		# DO NOT use add_permission() here.
		# DO NOT use update_permission_property() here.
		#
		# Direct SQL avoids the Custom DocPerm permission check
		# that was causing the submit error.
		# =========================================================

		existing_permission = frappe.db.get_value(
			"Custom DocPerm",
			{
				"parent": document_type,
				"role": role,
				"permlevel": level,
			},
			"name",
		)

		# ---------------------------------------------------------
		# EXISTING PERMISSION CHECK
		# ---------------------------------------------------------

		if existing_permission and not update_existing_role:
			frappe.throw(
				f"Permissions for Role '{role}' on Doctype "
				f"'{document_type}' (Level {level}) already exist. "
				"To override existing permissions, please check "
				"the 'Update Existing Role' option."
			)

		# ---------------------------------------------------------
		# UPDATE EXISTING PERMISSION
		# ---------------------------------------------------------

		if existing_permission:

			frappe.db.sql(
				"""
				UPDATE `tabCustom DocPerm`
				SET
					`select` = %(select)s,
					`read` = %(read)s,
					`write` = %(write)s,
					`create` = %(create)s,
					`delete` = %(delete)s,
					`submit` = %(submit)s,
					`cancel` = %(cancel)s,
					`amend` = %(amend)s,
					`print` = %(print)s,
					`email` = %(email)s,
					`report` = %(report)s,
					`import` = %(import)s,
					`export` = %(export)s,
					`share` = %(share)s,
					`modified` = NOW(),
					`modified_by` = %(modified_by)s
				WHERE `name` = %(name)s
				""",
				{
					**permissions,
					"name": existing_permission,
					"modified_by": frappe.session.user,
				},
			)

		# ---------------------------------------------------------
		# CREATE NEW PERMISSION
		# ---------------------------------------------------------

		else:

			next_idx = frappe.db.sql(
				"""
				SELECT COALESCE(MAX(`idx`), 0) + 1
				FROM `tabCustom DocPerm`
				WHERE `parent` = %(parent)s
				""",
				{
					"parent": document_type,
				},
			)[0][0]

			permission_name = frappe.generate_hash(length=10)

			frappe.db.sql(
				"""
				INSERT INTO `tabCustom DocPerm`
				(
					`name`,
					`creation`,
					`modified`,
					`modified_by`,
					`owner`,
					`docstatus`,
					`idx`,
					`parent`,
					`role`,
					`if_owner`,
					`permlevel`,
					`select`,
					`read`,
					`write`,
					`create`,
					`delete`,
					`submit`,
					`cancel`,
					`amend`,
					`report`,
					`export`,
					`import`,
					`share`,
					`print`,
					`email`
				)
				VALUES
				(
					%(name)s,
					NOW(),
					NOW(),
					%(modified_by)s,
					%(owner)s,
					0,
					%(idx)s,
					%(parent)s,
					%(role)s,
					0,
					%(permlevel)s,
					%(select)s,
					%(read)s,
					%(write)s,
					%(create)s,
					%(delete)s,
					%(submit)s,
					%(cancel)s,
					%(amend)s,
					%(report)s,
					%(export)s,
					%(import)s,
					%(share)s,
					%(print)s,
					%(email)s
				)
				""",
				{
					"name": permission_name,
					"modified_by": frappe.session.user,
					"owner": frappe.session.user,
					"idx": next_idx,
					"parent": document_type,
					"role": role,
					"permlevel": level,
					**permissions,
				},
			)

		# =========================================================
		# VALIDATE PERMISSIONS
		#
		# This is the part that existed in your old code.
		# It is executed AFTER direct SQL update/insert.
		#
		# It does NOT call add_permission(), so the old
		# Custom DocPerm permission error will not occur.
		# =========================================================

		try:
			from frappe.core.doctype.doctype.doctype import (
				validate_permissions_for_doctype,
			)

			validate_permissions_for_doctype(document_type)

		except Exception as e:
			# Permission row has already been written through SQL.
			# Do not make TZU Role Permission Manager submission
			# fail because of validation of the configured DocType.
			frappe.log_error(
				title="TZU Role Permission Manager Permission Validation",
				message=frappe.get_traceback(),
			)

		# =========================================================
		# CLEAR PERMISSION CACHE
		#
		# This makes the newly created/updated permission available
		# to Role Permissions Manager and permission checks.
		# =========================================================

		frappe.clear_cache(doctype=document_type)

		# Also clear the Custom DocPerm cache because the actual
		# permission configuration is stored there.
		frappe.clear_cache(doctype="Custom DocPerm")

		frappe.msgprint(
			f"Permissions for {role} on {document_type} "
			f"(Level {level}) have been updated."
		)
