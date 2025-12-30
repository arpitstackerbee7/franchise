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

// frappe.ui.form.on("Purchase Order", {
//     refresh: async function (frm) {

//         // 1️⃣ Sirf Submitted PO
//         if (frm.doc.docstatus !== 1) return;

//         // 2️⃣ Check Incoming Logistics exist ya nahi
//         const res = await frappe.db.get_value(
//             "Incoming Logistics",
//             { purchase_no: frm.doc.name },
//             "name"
//         );

//         // 3️⃣ Agar exist karti hai → button mat dikhao
//         if (res && res.message && res.message.name) {
//             return;
//         }

//         // 4️⃣ Button dikhao
//         frm.add_custom_button(
//             __("Incoming Logistics"),
//             async () => {

//                 let transporter = null;
//                 let gate_entry = "No";

//                 if (frm.doc.supplier) {
//                     const r = await frappe.db.get_value(
//                         "Supplier",
//                         frm.doc.supplier,
//                         ["custom_transporter", "custom_gate_entry"]
//                     );

//                     transporter = r?.message?.custom_transporter || null;
//                     gate_entry = r?.message?.custom_gate_entry ? "Yes" : "No";
//                 }

//                 frappe.new_doc("Incoming Logistics", {
//                     purchase_no: frm.doc.name,
//                     consignor: frm.doc.supplier,
//                     type: "Purchase",
//                     owner_site: frm.doc.company,
//                     transporter: transporter,
//                     gate_entry: gate_entry
//                 });
//             },
//             __("Create")
//         );
//     }
// });




frappe.ui.form.on("Purchase Order", {

    async refresh(frm) {

        // 1️⃣ Sirf Submitted PO
        if (frm.doc.docstatus !== 1) return;

        // 2️⃣ Supplier mandatory
        if (!frm.doc.supplier) return;

        // 3️⃣ Supplier se custom_gate_entry & transporter lao
        const supplier_res = await frappe.db.get_value(
            "Supplier",
            frm.doc.supplier,
            ["custom_gate_entry", "custom_transporter"]
        );

        const gate_entry_enabled = supplier_res?.message?.custom_gate_entry;
        const transporter = supplier_res?.message?.custom_transporter || null;

        // 4️⃣ Agar Supplier master me Gate Entry unchecked hai
        if (!gate_entry_enabled) {
            frappe.msgprint({
                title: __("Gate Entry Disabled"),
                message: __(
                    "Incoming Logistics cannot be created.<br><br>" +
                    "Please go to <b>Supplier </b> and enable <b>Gate Entry</b>."
                ),
                indicator: "orange"
            });
            return;
        }

        // 5️⃣ Check Incoming Logistics already exist ya nahi
        const il_res = await frappe.db.get_value(
            "Incoming Logistics",
            { purchase_no: frm.doc.name },
            "name"
        );

        // 6️⃣ Agar already exist karti hai → button mat dikhao
        if (il_res && il_res.message && il_res.message.name) {
            return;
        }

        // 7️⃣ Button dikhao
        frm.add_custom_button(
            __("Incoming Logistics"),
            () => {
                frappe.new_doc("Incoming Logistics", {
                    purchase_no: frm.doc.name,
                    consignor: frm.doc.supplier,
                    type: "Purchase",
                    owner_site: frm.doc.company,
                    transporter: transporter,
                    gate_entry: "Yes"
                });
            },
            __("Create")
        );
    }
});