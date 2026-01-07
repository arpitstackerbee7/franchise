
frappe.ui.form.on("Purchase Order", {

    async refresh(frm) {

        // 1️⃣ Only Submitted PO
        if (frm.doc.docstatus !== 1) return;
        if (!frm.doc.supplier) return;

        // 2️⃣ Supplier config
        const supplier_res = await frappe.db.get_value(
            "Supplier",
            frm.doc.supplier,
            ["custom_gate_entry", "custom_transporter"]
        );

        const gate_entry_enabled = supplier_res?.message?.custom_gate_entry;
        const transporter = supplier_res?.message?.custom_transporter;

        if (!gate_entry_enabled) {
            frappe.msgprint({
                title: __("Gate Entry Disabled"),
                message: __("Please enable <b>Gate Entry</b> in Supplier"),
                indicator: "orange"
            });
            return;
        }

        // 3️⃣ PO Total Qty
        let po_total_qty = 0;
        (frm.doc.items || []).forEach(row => {
            po_total_qty += flt(row.qty);
        });

        // 🔴 CHANGE #1 — Incoming Logistics ❌ parent se nahi
        // 🔴 CHANGE #2 — CHILD TABLE "Purchase Order ID" se qty uthao
        const il_list = await frappe.db.get_list("Purchase Order ID", {
            filters: {
                purchase_order: frm.doc.name,   // 🔴 CHANGED
                docstatus: 1
            },
        });

        let total_received_qty = 0;
        (il_list || []).forEach(row => {
            total_received_qty += flt(row.received_qty);
        });

        // 5️⃣ Remaining Qty
        let pending_qty = po_total_qty - total_received_qty;

        // ❌ Fully received → no button
        if (pending_qty <= 0) return;

        // ✅ Partial received → show button
        // frm.add_custom_button(
        //     __("Incoming Logistics"),
        //     () => {
        //         frappe.new_doc("Incoming Logistics", {

        //             // 🔴 CHANGE #3 — REMOVE this (parent field)
        //             // purchase_no: frm.doc.name,

        //             consignor: frm.doc.supplier,
        //             type: "Purchase",
        //             owner_site: frm.doc.company,
        //             transporter: transporter,
        //             gate_entry: "Yes",

        //             // 🔴 CHANGE #4 — PO ko CHILD TABLE me map karo
        //             purchase_order_id: [
        //                 {
        //                     purchase_order: frm.doc.name,
        //                     pending_qty: pending_qty
        //                 }
        //             ]
        //         });
        //     },
        //     __("Create")
        // );
        // Optional info
        frm.dashboard.add_comment(
            __("Pending Qty : {0}", [pending_qty]),
            "blue"
        );
    }
});
