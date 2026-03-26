# Copyright (c) 2025, Logedosoft Business Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def dn_validate(doc, method):
    """
    Validation hook for Delivery Note documents.
    Validates Yurtiçi Kargo related fields and settings.
    Only runs for submit operations (docstatus == 1).
    """
    frappe.log_error("VAL", method)
    print("=====TEST=======")
    # Only validate on submit, not on draft saves
    if doc.docstatus == 1:
        print("=====TEST=2======")
        # Validate that delivery method is set (it's a required field)
        if doc.custom_ld_delivery_method == "Yurtiçi Kargo":
            print("=====TEST=3======")
            # Check if prevention of submission without printing label is enabled
            settings = frappe.get_single("Yurtici Kargo Ayarlari")
            if settings.prevent_delivery_note_submission_without_printing_label:
                # Check if label has been printed
                print("=====TEST=4======")
                if not doc.custom_ld_yik_print_count or doc.custom_ld_yik_print_count == 0:
                    print("=====TEST=5======")
                    frappe.throw(
                        _("Önce Kargo etiketi yazdırın!")
                    )