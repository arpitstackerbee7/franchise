import frappe

from hrms.hr.doctype.full_and_final_statement.full_and_final_statement import (
    FullandFinalStatement as HRMSFullandFinalStatement,
)


class CustomFullandFinalStatement(HRMSFullandFinalStatement):

    def create_component_row(self, components, component_type):
        for component in components:

            account = self.get_component_account(component)

            self.append(
                component_type,
                {
                    "status": "Unsettled",
                    "reference_document_type": (
                        component
                        if component != "Bonus"
                        else "Additional Salary"
                    ),
                    "component": component,
                    "account": account,
                },
            )

    def get_component_account(self, component):
        """
        Fetch account from Salary Component > Accounts
        based on Component and Company.
        """

        if not component or not self.company:
            return None

        account = frappe.db.get_value(
            "Salary Component Account",
            {
                "parent": component,
                "parenttype": "Salary Component",
                "parentfield": "accounts",
                "company": self.company,
            },
            "account",
        )

        return account