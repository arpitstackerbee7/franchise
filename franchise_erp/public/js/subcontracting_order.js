// frappe.ui.form.on('Subcontracting Order', {
//     refresh(frm) {
//         if (frm.doc.docstatus !== 1 || !frm.doc.supplier) return;

//         // 1️⃣ First check if Stock Entry exists
//         frappe.db.exists("Stock Entry", {
//             subcontracting_order: frm.doc.name,
//             docstatus: 1
//         }).then(exists => {

//             if (!exists) return;  // ❌ If no stock entry, don't show button

//             // 2️⃣ If stock entry exists, then check Supplier flag
//             frappe.db.get_value(
//                 "Supplier",
//                 frm.doc.supplier,
//                 "custom_gate_out_applicable"
//             ).then(r => {

//                 if (r.message && r.message.custom_gate_out_applicable) {

//                     frm.add_custom_button(
//                         __('Outgoing Logistics'),
//                         () => {
//                             frappe.call({
//                                 method: "franchise_erp.custom.subcontracting_order.get_outgoing_logistics_data",
//                                 args: {
//                                     subcontracting_order: frm.doc.name
//                                 },
//                                 callback(r) {
//                                     if (r.message) {
//                                         frappe.new_doc("Outgoing Logistics", r.message);
//                                     }
//                                 }
//                             });
//                         },
//                         __('Create')
//                     );

//                 }
//             });

//         });
//     }
// });









frappe.ui.form.on('Subcontracting Order', {
    refresh(frm) {

        // ✅ Allow ONLY Open documents
        if (frm.doc.docstatus !== 0 || !frm.doc.supplier) return;

        // 🔁 Avoid duplicate buttons
        frm.remove_custom_button(__('Outgoing Logistics'), __('Create'));

        // 1️⃣ Check Stock Entry exists
        frappe.db.exists("Stock Entry", {
            subcontracting_order: frm.doc.name,
            docstatus: 1
        }).then(exists => {

            if (!exists) return;

            // 2️⃣ Check Supplier flag
            frappe.db.get_value(
                "Supplier",
                frm.doc.supplier,
                "custom_gate_out_applicable"
            ).then(r => {

                if (!r.message?.custom_gate_out_applicable) return;

                // 3️⃣ Add button
                frm.add_custom_button(
                    __('Outgoing Logistics'),
                    () => {
                        frappe.call({
                            method: "franchise_erp.custom.subcontracting_order.get_outgoing_logistics_data",
                            args: {
                                subcontracting_order: frm.doc.name
                            },
                            freeze: true,
                            callback(res) {
                                if (res.message) {
                                    frappe.new_doc("Outgoing Logistics", res.message);
                                }
                            }
                        });
                    },
                    __('Create')
                );
            });
        });
    }
});
