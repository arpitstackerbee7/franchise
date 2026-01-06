# Copyright (c) 2026, Franchise Erp and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class TZURolePermissionManager(Document):

	def on_submit(doc):
		from frappe.permissions import add_permission, update_permission_property

		# Get data from the submitted document
		document_type = doc.document_type
		role = doc.role
		level = doc.level or 0  # Default to level 0 if not provided
		update_existing_role = doc.update_existing_role

		# Define permissions to be set
		permissions = {
			"select": doc.select_,
			"read": doc.read_,
			"write": doc.write_,
			"create": doc.create_,
			"delete": doc.delete_,
			"submit": doc.submit_,
			"cancel": doc.cancel_,
			"amend": doc.amend_,
			"print": doc.print_,
			"email": doc.email_,
			"report": doc.report_,
			"import": doc.import_,
			"export": doc.export_,
			"share": doc.share_,
		}

		# Check if existing permissions for the role and Doctype exist
		existing_permissions = frappe.db.exists(
			"Custom DocPerm", {"parent": document_type, "role": role, "permlevel": level}
		)

		if existing_permissions and not update_existing_role:
			# Throw an error if update_existing_role is not checked and permissions exist
			frappe.throw(
				f"Permissions for Role '{role}' on Doctype '{document_type}' (Level {level}) already exist. "
				"To override existing permissions, please check the 'Update Existing Role' option."
			)

		# Iterate through permissions and set them
		for perm_type, value in permissions.items():
			if value:
				# Enable permission
				add_permission(document_type, role, permlevel=level)
				update_permission_property(
					doctype=document_type,
					role=role,
					permlevel=level,
					ptype=perm_type,
					value=1,
					validate=False,  # Set to True after all changes
				)
			else:
				# Disable permission
				update_permission_property(
					doctype=document_type,
					role=role,
					permlevel=level,
					ptype=perm_type,
					value=0,
					validate=False,  # Set to True after all changes
				)

		# Validate permissions once after all updates
		from frappe.core.doctype.doctype.doctype import validate_permissions_for_doctype
		validate_permissions_for_doctype(document_type)

		frappe.msgprint(f"Permissions for {role} on {document_type} (Level {level}) have been updated.")


