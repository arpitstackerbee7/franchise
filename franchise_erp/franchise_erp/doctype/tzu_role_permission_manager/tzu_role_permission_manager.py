
# Copyright (c) 2026, Franchise Erp and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class TZURolePermissionManager(Document):

	def validate(self):
		# Custom DocPerm configuration ko manager ke through
		# karte waqt permission/link validation se block na kare.
		if self.document_type == "Custom DocPerm":
			self.flags.ignore_permissions = True
			self.flags.ignore_links = True

	def check_permission(self, permtype="read", permlevel=None):
		"""
		Allow TZU Role Permission Manager to submit when it is
		configuring Custom DocPerm.

		No direct Custom DocPerm permission is required from
		the current user.
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
		# Custom DocPerm itself is a special/core permission
		# configuration.
		#
		# Actual table:
		#     tabDocPerm
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
			# UPDATE
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
			# CREATE
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

			frappe.clear_cache(doctype="Custom DocPerm")

			frappe.msgprint(
				f"Permissions for {role} on Custom DocPerm "
				f"(Level {level}) have been updated."
			)

			return

		# =========================================================
		# NORMAL DOCTYPES
		#
		# Actual table:
		#     tabCustom DocPerm
		#
		# IMPORTANT:
		# Do NOT use add_permission().
		# Do NOT use update_permission_property().
		#
		# Both can trigger Custom DocPerm permission checks.
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
		# CLEAR PERMISSION CACHE
		# =========================================================

		frappe.clear_cache(doctype=document_type)

		frappe.msgprint(
			f"Permissions for {role} on {document_type} "
			f"(Level {level}) have been updated."
		)

	# def on_submit(doc):
	# 	from frappe.permissions import add_permission, update_permission_property

	# 	# Get data from the submitted document
	# 	document_type = doc.document_type
	# 	role = doc.role
	# 	level = doc.level or 0  # Default to level 0 if not provided
	# 	update_existing_role = doc.update_existing_role

	# 	# Define permissions to be set
	# 	permissions = {
	# 		"select": doc.select_,
	# 		"read": doc.read_,
	# 		"write": doc.write_,
	# 		"create": doc.create_,
	# 		"delete": doc.delete_,
	# 		"submit": doc.submit_,
	# 		"cancel": doc.cancel_,
	# 		"amend": doc.amend_,
	# 		"print": doc.print_,
	# 		"email": doc.email_,
	# 		"report": doc.report_,
	# 		"import": doc.import_,
	# 		"export": doc.export_,
	# 		"share": doc.share_,
	# 	}

	# 	# Check if existing permissions for the role and Doctype exist
	# 	existing_permissions = frappe.db.exists(
	# 		"Custom DocPerm", {"parent": document_type, "role": role, "permlevel": level}
	# 	)

	# 	if existing_permissions and not update_existing_role:
	# 		# Throw an error if update_existing_role is not checked and permissions exist
	# 		frappe.throw(
	# 			f"Permissions for Role '{role}' on Doctype '{document_type}' (Level {level}) already exist. "
	# 			"To override existing permissions, please check the 'Update Existing Role' option."
	# 		)

	# 	# Iterate through permissions and set them
	# 	for perm_type, value in permissions.items():
	# 		if value:
	# 			# Enable permission
	# 			add_permission(document_type, role, permlevel=level)
	# 			update_permission_property(
	# 				doctype=document_type,
	# 				role=role,
	# 				permlevel=level,
	# 				ptype=perm_type,
	# 				value=1,
	# 				validate=False,  # Set to True after all changes
	# 			)
	# 		else:
	# 			# Disable permission
	# 			update_permission_property(
	# 				doctype=document_type,
	# 				role=role,
	# 				permlevel=level,
	# 				ptype=perm_type,
	# 				value=0,
	# 				validate=False,  # Set to True after all changes
	# 			)

	# 	# Validate permissions once after all updates
	# 	from frappe.core.doctype.doctype.doctype import validate_permissions_for_doctype
	# 	validate_permissions_for_doctype(document_type)

	# 	frappe.msgprint(f"Permissions for {role} on {document_type} (Level {level}) have been updated.")


