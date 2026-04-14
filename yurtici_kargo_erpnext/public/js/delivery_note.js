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
			// Ask box qty
			frappe.prompt({
				label: __('Koli Adedi'),
				fieldname: 'label_qty',
				fieldtype: 'Int'
			}, ( values ) => {
				// Print the label label_qty times sequentially
				let dIdx = 0;
				function printNextLabel() {
					if (dIdx >= values.label_qty) return;
					const url = frappe.urllib.get_full_url(
						"/printview?"
						+ "doctype=" + encodeURIComponent(frm.doctype)
						+ "&name=" + encodeURIComponent(frm.docname)
						+ "&format=" + encodeURIComponent("Yurtiçi Kargo İrsaliye Etiketi")
						+ "&label_no=" + (dIdx + 1)
						+ "&label_count=" + values.label_qty
						+ "&no_letterhead=1"
						+ "&trigger_print=1"
						+ "&lang=tr"
					);
					const w = window.open(url);
					if (w) {
						w.onafterprint = () => {
							w.close();
							dIdx++;
							printNextLabel();
						};
					} else {
						dIdx++;
						printNextLabel();
					}
				}
				printNextLabel();
			});
		}, __("Kargo Etiketi Yazdır"));
	}
});