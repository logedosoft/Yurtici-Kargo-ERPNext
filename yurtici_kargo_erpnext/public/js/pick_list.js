// Copyright (c) 2025, Logedosoft Business Solutions and contributors
// For license information, please see license.txt

frappe.ui.form.on("Pick List", {
	refresh(frm) {
		//Create custom button to dırectly print 
		frm.add_custom_button(__("Yurtiçi Kargo"), function() {
			const url = frappe.urllib.get_full_url(
				"/printview?"
				+ "doctype=" + encodeURIComponent(frm.doctype)
				+ "&name=" + encodeURIComponent(frm.docname)
				+ "&format=" + encodeURIComponent("Yurtiçi Kargo Etiketi")
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