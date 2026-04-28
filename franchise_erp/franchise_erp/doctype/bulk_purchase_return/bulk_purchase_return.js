frappe.ui.form.on("Bulk Purchase Return", {
    refresh(frm) {

        if (frm.is_new() || frm.doc.docstatus !== 0) return;

        frm.add_custom_button("Get Items from GRN", () => {
            open_return_items_dialog(frm);
        });

    }
});


frappe.ui.form.on('Bulk Purchase Return', {
    refresh: function(frm) {

        if (frm.doc.docstatus !== 1) return;

        frappe.call({
            method: 'franchise_erp.franchise_erp.doctype.bulk_purchase_return.bulk_purchase_return.has_draft_return_prs',
            args: {
                docname: frm.doc.name
            },
            callback: function(r) {

                if (r.message) {

                    frm.add_custom_button('Submit Return PRs', async function() {

                        await frappe.call({
                            method: 'franchise_erp.franchise_erp.doctype.bulk_purchase_return.bulk_purchase_return.submit_created_prs',
                            args: {
                                docname: frm.doc.name
                            },
                            freeze: true,
                            freeze_message: 'Submitting in background...'
                        });
                    
                        frappe.msgprint("Submission started in background.");
                    
                        frm.reload_doc();
                    });
                }
            }
        });
    }
});

function open_return_items_dialog(frm) {

    let dialog = new frappe.ui.Dialog({
        title: "Return Items from GRN",
        size: "extra-large",

        fields: [
            {
                fieldname: "supplier",
                label: "Supplier",
                fieldtype: "Link",
                options: "Supplier",
                default: frm.doc.supplier,
                read_only:1,
                reqd: 1,
                onchange() {
                    load_returnable_items(frm, dialog);
                }
            },

            {
                fieldname: "item_code",
                label: "Item",
                fieldtype: "Link",
                options: "Item",
                onchange() {
                    load_returnable_items(frm, dialog);
                }
            },
            {
                fieldname: "serial_no",
                label: "Scan Serial",
                fieldtype: "Data",
            
                onchange() {
            
                    let serial = dialog.get_value("serial_no");
                    if (!serial) return;
            
                    frappe.call({
                        method: "franchise_erp.franchise_erp.doctype.bulk_purchase_return.bulk_purchase_return.get_pr_from_serial",
                        args: {
                            serial_no: serial,
                            company: frm.doc.company
                        },
            
                        callback: function(r) {

                            if (!r.message) {
                                frappe.msgprint(`Serial ${serial} not found`);
                                dialog.set_value("serial_no", "");
                                return;
                            }
                        
                            // ❌ Condition 1 — Serial status Delivered
                            if (r.message.status === "Delivered") {
                                frappe.msgprint(`Serial ${serial} is already Delivered and cannot be returned.`);
                                dialog.set_value("serial_no", "");
                                dialog.fields_dict.serial_no.$input.focus();
                                return;
                            }
                        
                            // ❌ Condition 2 — Serial already exists in Items child table
                            let serial_exists = false;
                        
                            (frm.doc.items || []).forEach(row => {
                                if (row.serial_nos && row.serial_nos.split("\n").includes(serial)) {
                                    serial_exists = true;
                                }
                            });
                        
                            if (serial_exists) {
                                frappe.msgprint(`Serial ${serial} already exists in the Items table.`);
                                dialog.set_value("serial_no", "");
                                dialog.fields_dict.serial_no.$input.focus();
                                return;
                            }
                        
                            let table = dialog.fields_dict.items_table.grid;
                            let rows = table.get_data();

                            let index = rows.findIndex(d =>
                                d.purchase_receipt === r.message.purchase_receipt &&
                                d.item_code === r.message.item_code
                            );

                            if (index !== -1) {

                                let existing = rows[index];

                                // Prevent duplicate serial
                                if (existing.serial_nos && existing.serial_nos.split("\n").includes(serial)) {
                                    frappe.msgprint(`Serial ${serial} already scanned`);
                                } else {

                                    existing.return_qty = (existing.return_qty || 0) + 1;

                                    existing.serial_nos =
                                        existing.serial_nos
                                            ? existing.serial_nos + "\n" + serial
                                            : serial;

                                    // 🔥 MOVE UPDATED ROW TO TOP
                                    rows.splice(index, 1);   // remove from current position
                                    rows.unshift(existing);  // add to top
                                }

                            } else {

                                r.message.return_qty = 1;
                                r.message.serial_nos = serial;

                                // 🔥 ADD NEW ROW TO TOP
                                rows.unshift(r.message);
                            }

                            table.refresh();
                            
                            // 🔥 Auto-select the scanned row
                            // 🔥 FORCE checkbox selection (reliable for dialog grids)
                            // 🔥 Wait until grid is actually rendered
                            frappe.after_ajax(() => {
                                setTimeout(() => {
                                    let grid = dialog.fields_dict.items_table.grid;
                            
                                    if (grid.grid_rows.length) {
                                        let row = grid.grid_rows[0];
                            
                                        let checkbox = row.wrapper.find('.grid-row-check');
                            
                                        // ✅ Only click if NOT already checked
                                        if (!checkbox.prop("checked")) {
                                            checkbox.click();
                                        }
                                    }
                                }, 200);
                            });
                            dialog.set_value("serial_no", "");
                            dialog.fields_dict.serial_no.$input.focus();
                        }
                    });
                }
            },

            {
                fieldname: "items_table",
                fieldtype: "Table",
                label: "Items",
                cannot_add_rows: true,
                in_place_edit: true,

                fields: [

                    { fieldname: "purchase_receipt", label: "GRN", fieldtype: "Data", read_only: 1, in_list_view: 1},

                    { fieldname: "item_code", label: "Item", fieldtype: "Data", read_only: 1, in_list_view: 1},
                    
                    { fieldname: "returnable_qty", label: "Returnable Qty", fieldtype: "Float", read_only: 1, in_list_view: 1 },
                    
                    { fieldname: "returned_qty", label: "Already Returned", fieldtype: "Float", read_only: 1, in_list_view: 1},

                    {
                        fieldname: "return_qty",
                        label: "Return Qty",
                        fieldtype: "Float",
                        in_list_view: 1,
                        onchange() {
                    
                            let grid = dialog.fields_dict.items_table.grid;
                            let row = grid.get_row(this.doc.name);
                            let d = row.doc;
                    
                            // Serialized item rule
                            if (d.has_serial_no == 1) {
                    
                                let serial_count = 0;
                    
                                if (d.serial_nos) {
                                    serial_count = d.serial_nos
                                        .split("\n")
                                        .filter(s => s.trim()).length;
                                }
                    
                                if (serial_count === 0) {
                    
                                    frappe.msgprint(
                                        __("Scan Serial Numbers first for serialized item {0}.", [d.item_code])
                                    );
                    
                                    d.return_qty = 0;
                                    grid.refresh();
                                    return;
                                }
                    
                                // always sync qty with serial count
                                d.return_qty = serial_count;
                    
                                grid.refresh();
                                return;
                            }
                    
                            // Normal validation for non-serialized
                            if (flt(d.return_qty) > flt(d.returnable_qty)) {
                    
                                frappe.msgprint(
                                    __("Return Qty cannot exceed Returnable Qty for Item {0}", [d.item_code])
                                );
                    
                                d.return_qty = d.returnable_qty;
                                grid.refresh();
                            }
                        }
                    },

                    { fieldname: "serial_nos", label: "Serial Nos", fieldtype: "Small Text", read_only: 1, in_list_view: 1},

                ]
            }
        ],

        primary_action_label: "Add Selected Items",

        primary_action() {

            let selected_rows =
                dialog.fields_dict.items_table.grid.get_selected_children();
        
            if (!selected_rows.length) {
                frappe.msgprint("Please select rows");
                return;
            }
        
            // 🔴 Validate return qty in dialog
            for (let r of selected_rows) {
        
                if (!r.return_qty || r.return_qty <= 0) {
                    frappe.throw(
                        `Please enter Return Qty for Item ${r.item_code} in GRN ${r.purchase_receipt}`
                    );
                }
        
                if (r.return_qty > r.returnable_qty) {
                    frappe.throw(
                        `Return Qty cannot exceed Returnable Qty for Item ${r.item_code} in GRN ${r.purchase_receipt}`
                    );
                }
            }
            let merged_rows = {};

            selected_rows.forEach(d => {

                let key = d.purchase_receipt_item;

                if (!merged_rows[key]) {
                    merged_rows[key] = {...d};
                } else {

                    merged_rows[key].return_qty =
                        flt(merged_rows[key].return_qty) + flt(d.return_qty);

                    if (d.serial_nos) {

                        merged_rows[key].serial_nos =
                            (merged_rows[key].serial_nos || "") +
                            "\n" +
                            d.serial_nos;
                    }
                }

            });
        
            selected_rows = Object.values(merged_rows);

            frappe.call({
                method: "franchise_erp.franchise_erp.doctype.bulk_purchase_return.bulk_purchase_return.get_pr_item_details",
                args: {
                    items: selected_rows
                },
                callback: function(r) {

                    if (r.message) {

                        try {

                            r.message.forEach(d => {

                                let existing = frm.doc.items.find(row =>
                                    row.purchase_receipt_item === d.name &&
                                    row.warehouse === d.warehouse
                                );
                                if (existing) {

                                    let new_qty = flt(existing.qty) + flt(d.qty);
                                
                                    // validation
                                    if (new_qty > flt(existing.returnable_quantity)) {
                                        frappe.throw(
                                            __("Return Qty exceeded for Item {0}. Allowed Qty: {1}", 
                                            [existing.item_code, existing.returnable_quantity])
                                        );
                                        return;
                                    }
                                
                                    frappe.model.set_value(
                                        existing.doctype,
                                        existing.name,
                                        "qty",
                                        new_qty
                                    );
                                
                                    if (d.serial_nos) {
                                
                                        let existing_serials = existing.serial_nos
                                            ? existing.serial_nos.split("\n")
                                            : [];
                                
                                        let new_serials = d.serial_nos
                                            ? d.serial_nos.split("\n")
                                            : [];
                                
                                        let merged = [...new Set([...existing_serials, ...new_serials])];
                                
                                        frappe.model.set_value(
                                            existing.doctype,
                                            existing.name,
                                            "serial_nos",
                                            merged.join("\n")
                                        );
                                    }
                                
                                    frappe.model.set_value(
                                        existing.doctype,
                                        existing.name,
                                        "available_serial_nos",
                                        d.available_serial_nos
                                    );
                                }
                                 else {

                                    let row = frm.add_child("items");

                                    row.purchase_receipt = d.purchase_receipt;
                                    row.purchase_receipt_item = d.name;
                                    row.item_code = d.item_code;
                                    row.item_name = d.item_name;
                                    row.qty = d.qty;
                                    row.uom = d.uom;
                                    row.stock_uom = d.stock_uom;
                                    row.conversion_factor = d.conversion_factor;
                                    row.rate = d.rate;
                                    row.warehouse = d.warehouse;
                                    row.returnable_quantity = d.returnable_quantity;

                                    frappe.model.set_value(row.doctype, row.name, "serial_nos", d.serial_nos);
                                    frappe.model.set_value(row.doctype, row.name, "available_serial_nos", d.available_serial_nos);
                                }

                            });

                        } catch (e) {
                            console.error("Error adding items:", e);
                        }

                        frm.refresh_field("items");

                        dialog.hide();
                    }
                }
            });
            }
        });

    dialog.show();

        setTimeout(() => {

    let field = dialog.fields_dict.serial_no;
    let input = field.$input;
    let wrapper = field.$wrapper;

    wrapper.css({
        position: "relative",
        overflow: "hidden"
    });

    input.css({
        height: "35px",
        "border-radius": "8px",
        "padding-right": "40px"
    });

    wrapper.find(".scan-btn").remove();

    let btn = $(`
    <button class="scan-btn btn btn-default" style="
        position:absolute;
        right:8px;
        top:55%;
        transform:translateY(-50%);
        height:28px;
        width:28px;
        padding:0;
        display:flex;
        align-items:center;
        justify-content:center;
        border-radius:6px;
        z-index:5;
    ">
        <i class="fa fa-camera"></i>
    </button>
    `);

    wrapper.append(btn);

    input.focus();
    input.attr("autocomplete", "off");

    input.on("keydown", function(e){
        if(e.key === "Enter"){
            e.preventDefault();
            input.trigger("change");
        }
    });

    // 🔥 CAMERA CLICK
        btn.on("click", function () {

    openScanner(function(code) {
        dialog.set_value("serial_no", code);
        input.trigger("change");
    });

});

}, 300);

    load_returnable_items(frm,dialog);
}


function load_returnable_items(frm, dialog) {

    let supplier = dialog.get_value("supplier");
    let item_code = dialog.get_value("item_code");

    if (!supplier) return;

    frappe.call({
        method: "franchise_erp.franchise_erp.doctype.bulk_purchase_return.bulk_purchase_return.get_returnable_items",
        args: {
            supplier: supplier,
            item_code: item_code,
            company: frm.doc.company
        },
        callback: function(r) {

            if (!r.message) return;

            dialog.fields_dict.items_table.df.data = r.message;
            dialog.fields_dict.items_table.grid.refresh();

        }
    });
}

function openScanner(callback) {

    let scanner_dialog = new frappe.ui.Dialog({
        title: "Scan Barcode",
        size: "large",
        fields: [
            { fieldtype: "HTML", fieldname: "scanner" }
        ]
    });

    scanner_dialog.show();

    setTimeout(() => {

        let target = scanner_dialog.fields_dict.scanner.$wrapper.get(0);

        // 🔥 FIX SIZE
        target.style.height = "400px";
        target.style.width = "100%";
        target.style.position = "relative";
        target.style.overflow = "hidden";

        // 🔥 DARK MASK
        let mask = document.createElement("div");
        mask.style.position = "absolute";
        mask.style.top = "0";
        mask.style.left = "0";
        mask.style.width = "100%";
        mask.style.height = "100%";
        mask.style.background = "rgba(0,0,0,0.6)";
        mask.style.zIndex = "1";

        // 🔥 SCAN BOX
        let box = document.createElement("div");
        box.style.position = "absolute";
        box.style.width = "260px";
        box.style.height = "260px";
        box.style.top = "50%";
        box.style.left = "50%";
        box.style.transform = "translate(-50%, -50%)";
        box.style.border = "3px solid #fff";
        box.style.borderRadius = "12px";
        box.style.zIndex = "2";

        // 🔥 CUT EFFECT
        box.style.boxShadow = "0 0 0 9999px rgba(0,0,0,0.6)";

        // 🔥 SCAN LINE
        let line = document.createElement("div");
        line.style.position = "absolute";
        line.style.width = "100%";
        line.style.height = "2px";
        line.style.background = "red";
        line.style.top = "0";
        line.style.animation = "scanMove 2s linear infinite";
        box.appendChild(line);

        // animation
        let style = document.createElement("style");
        style.innerHTML = `
        @keyframes scanMove {
            0% { top: 0; }
            100% { top: 100%; }
        }`;
        document.head.appendChild(style);

        target.appendChild(mask);
        target.appendChild(box);

        frappe.require("https://cdnjs.cloudflare.com/ajax/libs/quagga/0.12.1/quagga.min.js", () => {

            let isScanned = false;

            Quagga.init({
                inputStream: {
                    type: "LiveStream",
                    target: target,
                    constraints: {
                        facingMode: "environment"
                    },
                    area: {
                        top: "25%",
                        right: "25%",
                        left: "25%",
                        bottom: "25%"
                    }
                },
                locator: {
                    patchSize: "medium",
                    halfSample: true
                },
                decoder: {
                    readers: [
                        "code_128_reader",
                        "ean_reader",
                        "ean_8_reader"
                    ]
                },
                locate: true
            }, function (err) {

                if (err) {
                    frappe.msgprint("Camera init failed");
                    return;
                }

                Quagga.start();

                setTimeout(() => {
                    window.dispatchEvent(new Event('resize'));
                }, 200);
            });

            Quagga.offDetected();

            Quagga.onDetected(function (result) {

                if (isScanned) return;
                isScanned = true;

                let code = result.codeResult.code;

                if (callback) callback(code);

                setTimeout(() => {
                    stopScanner();
                    scanner_dialog.hide();
                }, 200);
            });

            function stopScanner() {
                try {
                    if (Quagga) {
                        Quagga.stop();

                        let stream = Quagga.CameraAccess?.getActiveStream();
                        if (stream) {
                            stream.getTracks().forEach(track => track.stop());
                        }
                    }
                } catch (e) {}
            }

            scanner_dialog.$wrapper.on("hidden.bs.modal", function () {
                stopScanner();
            });

        });

    }, 300);
}