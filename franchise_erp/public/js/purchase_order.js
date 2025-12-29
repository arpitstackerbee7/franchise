// frappe.ui.form.on("Purchase Order", {
//     refresh(frm) {

//         if (frm.doc.docstatus !== 1) return;

//         frm.add_custom_button(
//             __("Incoming Logistics"),
//             () => {
//                 frappe.new_doc("Incoming Logistics", {
//                     purchase_no: frm.doc.name,   // ✅ Incoming Logistics fieldname
//                     consignor: frm.doc.supplier,    // ✅ Incoming Logistics fieldname
//                     type: 'Purchase',
//                     owner_site: frm.doc.company,
//                     transporter: frm.doc.custom_transporter || null   // auto fill
//                 });
//             },
//             __("Create")
//         );
//     }
// });

frappe.ui.form.on("Purchase Order", {
    supplier(frm) {
        if (!frm.doc.supplier) {
            frm.set_value("custom_agent_supplier", null);
            frm.set_value("custom_transporter_supplier", null);
            return;
        }

        frappe.db.get_value(
            "Supplier",
            frm.doc.supplier,
            ["custom_is_agent", "is_transporter","custom_agent_supplier","custom_transporter_supplier"],
            (r) => {
                console.log("tst------------",r)
                // If the supplier is an agent, then set the Agent as the Supplier as well.
                if (r.custom_is_agent) {
                    frm.set_value("custom_agent_supplier", r.custom_agent_supplier);
                } else {
                    frm.set_value("custom_agent_supplier", null);
                }

                // If the supplier is a transporter, then set the Transporter as the Supplier.
                if (r.is_transporter) {
                    frm.set_value("custom_transporter_supplier", r.custom_transporter_supplier);
                } else {
                    frm.set_value("custom_transporter_supplier", null);
                }
            }
    refresh: async function (frm) {

        // 1️⃣ Sirf Submitted PO
        if (frm.doc.docstatus !== 1) return;

        // 2️⃣ Check Incoming Logistics exist ya nahi
        const res = await frappe.db.get_value(
            "Incoming Logistics",
            { purchase_no: frm.doc.name },
            "name"
        );

        // 3️⃣ Agar exist karti hai → button mat dikhao
        if (res && res.message && res.message.name) {
            return;
        }

        // 4️⃣ Button dikhao
        frm.add_custom_button(
            __("Incoming Logistics"),
            async () => {

                let transporter = null;
                let gate_entry = "No";

                if (frm.doc.supplier) {
                    const r = await frappe.db.get_value(
                        "Supplier",
                        frm.doc.supplier,
                        ["custom_transporter", "custom_gate_entry"]
                    );

                    transporter = r?.message?.custom_transporter || null;
                    gate_entry = r?.message?.custom_gate_entry ? "Yes" : "No";
                }

                frappe.new_doc("Incoming Logistics", {
                    purchase_no: frm.doc.name,
                    consignor: frm.doc.supplier,
                    type: "Purchase",
                    owner_site: frm.doc.company,
                    transporter: transporter,
                    gate_entry: gate_entry
                });
            },
            __("Create")
        );
    }
});

