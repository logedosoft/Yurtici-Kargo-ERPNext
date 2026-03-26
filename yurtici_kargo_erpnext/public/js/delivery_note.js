// Copyright (c) 2025, Logedosoft Business Solutions and contributors
// For license information, please see license.txt

frappe.ui.form.on("Delivery Note", {
	refresh(frm) {
		//Create custom button to directly print 
		frm.add_custom_button(__("Yurtiçi Kargo"), function() {
			//Increment custom_ld_yik_print_count field by 1
			let dPrintCount = frm.doc.custom_ld_yik_print_count || 0;
			frappe.db.set_value("Delivery Note", frm.docname, "custom_ld_yik_print_count", dPrintCount + 1).then( (doc) => {
				frm.reload_doc();
			});
			// Print the label
			const url = frappe.urllib.get_full_url(
				"/printview?"
				+ "doctype=" + encodeURIComponent(frm.doctype)
				+ "&name=" + encodeURIComponent(frm.docname)
				+ "&format=" + encodeURIComponent("Yurtiçi Kargo İrsaliye Etiketi")
				+ "&no_letterhead=1"
				+ "&trigger_print=1"
				+ "&lang=tr"
			);
			const w = window.open(url);
			// Close the tab automatically after print dialog is dismissed
			if (w) {
				w.onafterprint = () => w.close();
			}
		}, __("Kargo Etiketi Yazdır"));
	}
});