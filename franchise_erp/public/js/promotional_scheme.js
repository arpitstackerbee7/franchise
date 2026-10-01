frappe.ui.form.on("Promotional Scheme Price Discount", {
    custom_get_1_free(frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        if (row.custom_get_1_free && row.custom_get_50_off) {
            row.custom_get_1_free = 0;
            frappe.msgprint({
                title: __("Validation Error"),
                message: __("To keep this checked, please uncheck the Buy n Get 50% off field."),
                indicator: "red"
            });
            frm.refresh_field("price_discount_slabs");
        }
    },

    custom_get_50_off(frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        if (row.custom_get_50_off && row.custom_get_1_free) {
            row.custom_get_50_off = 0;
            frappe.msgprint({
                title: __("Validation Error"),
                message: __("To keep this checked, please uncheck the Buy n Get 1 Free field."),
                indicator: "red"
            });
            frm.refresh_field("price_discount_slabs");
        }
    },
    custom_enter_1: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        // Only validate if the checkbox is checked
        if (row.custom_get_1_free) {
            if (!row.custom_enter_1 || row.custom_enter_1 < 1) {
                frappe.msgprint(__('Please enter a valid number of items for Buy X Get 1 Free.'));
                // Reset the field so user must re-enter a valid number
                frappe.model.set_value(cdt, cdn, 'custom_enter_1', 1);
            }
        }
    },
    custom_enter_50: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        // Only validate if the checkbox is checked
        if (row.custom_get_50_off) {
            if (!row.custom_enter_50 || row.custom_enter_50 < 1) {
                frappe.msgprint(__('Please enter a valid number of items for Buy X Get 50% Off.'));
                // Reset the field to blank so user must re-enter
                frappe.model.set_value(cdt, cdn, 'custom_enter_50', 1);
            }
        }
    }
});
frappe.ui.form.on("Promotional Scheme", {
    refresh(frm) {
        setTimeout(() => {
            add_restricted_item_code_buttons(frm);
        }, 300);
    }
});


function add_restricted_item_code_buttons(frm) {
    const field = frm.fields_dict.custom_restricted_item_code;

    if (!field || !field.grid) {
        return;
    }

    const $wrapper = $(field.grid.wrapper);

    // Remove buttons if already added
    $wrapper.find(".restricted-item-code-buttons").remove();

    const $footer = $wrapper.find(".grid-footer");

    if (!$footer.length) {
        return;
    }

    // Button container
    const $buttons = $(`
        <div class="restricted-item-code-buttons"
            style="
                margin-left: auto;
                display: flex;
                align-items: center;
                gap: 4px;
            ">
        </div>
    `);

    // Upload
    const $upload = $(`
        <button type="button"
            class="btn btn-xs btn-default">
            ${__("Upload")}
        </button>
    `);

    $upload.on("click", function () {
        upload_restricted_item_code(frm);
    });


    // Download
    const $download = $(`
        <button type="button"
            class="btn btn-xs btn-default">
            ${__("Download")}
        </button>
    `);

    $download.on("click", function () {
        download_restricted_item_code(frm);
    });


    
    $buttons.append($download);
    $buttons.append($upload);
    /*
     * Keep pagination on left
     * and Upload / Download on right
     */
    $footer.css({
        display: "flex",
        alignItems: "center"
    });

    $footer.append($buttons);
}


/* =========================================================
   DOWNLOAD
   ========================================================= */

function download_restricted_item_code(frm) {

    const rows = frm.doc.custom_restricted_item_code || [];

    if (!rows.length) {
        frappe.msgprint(__("No Restricted Item Code rows found."));
        return;
    }

    const data = rows.map(row => ({
        item_code: row.item_code || "",
        item_name: row.item_name || ""
    }));

    const headers = Object.keys(data[0]);

    let csv = headers.join(",") + "\n";

    data.forEach(row => {
        csv += headers.map(field => {
            const value = String(row[field] ?? "")
                .replace(/"/g, '""');

            return `"${value}"`;
        }).join(",") + "\n";
    });

    const blob = new Blob(
        [csv],
        { type: "text/csv;charset=utf-8;" }
    );

    const url = URL.createObjectURL(blob);

    const link = document.createElement("a");

    link.href = url;
    link.download = "restricted_item_code.csv";

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    URL.revokeObjectURL(url);
}


/* =========================================================
   UPLOAD
   ========================================================= */

function upload_restricted_item_code(frm) {

    new frappe.ui.FileUploader({

        doctype: frm.doctype,
        docname: frm.docname,

        restrictions: {
            allowed_file_types: [".csv"]
        },

        on_success(file) {

            frappe.msgprint(
                __("File uploaded successfully.")
            );

        }
    });
}