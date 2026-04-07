// Copyright (c) 2026, Logedosoft Business Solutions and contributors
// For license information, please see license.txt

frappe.ui.form.on("Yurtici Kargo Ayarlari", {
	test_connection(frm) {
        //Call utils.py test_connection function
        frappe.call({
            method: "yurtici_kargo_erpnext.utils.test_connection",
            args: {
                docYIKSettings: frm.doc
            },
            callback: function(r) {
                if (r.message) {
                    frappe.msgprint(r.message.op_message);
                }
            }
        });
	},
});
