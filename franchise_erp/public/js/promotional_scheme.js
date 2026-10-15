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

// function download_restricted_item_code(frm) {

//     const rows = frm.doc.custom_restricted_item_code || [];

//     if (!rows.length) {
//         frappe.msgprint(__("No Restricted Item Code rows found."));
//         return;
//     }

//     const data = rows.map(row => ({
//         item_code: row.item_code || "",
//         item_name: row.item_name || ""
//     }));

//     const headers = Object.keys(data[0]);

//     let csv = headers.join(",") + "\n";

//     data.forEach(row => {
//         csv += headers.map(field => {
//             const value = String(row[field] ?? "")
//                 .replace(/"/g, '""');

//             return `"${value}"`;
//         }).join(",") + "\n";
//     });

//     const blob = new Blob(
//         [csv],
//         { type: "text/csv;charset=utf-8;" }
//     );

//     const url = URL.createObjectURL(blob);

//     const link = document.createElement("a");

//     link.href = url;
//     link.download = "restricted_item_code.csv";

//     document.body.appendChild(link);
//     link.click();
//     document.body.removeChild(link);

//     URL.revokeObjectURL(url);
// }
/* =========================================================
   DOWNLOAD SAMPLE / EXISTING DATA
   ========================================================= */

function download_restricted_item_code(frm) {

    const rows = frm.doc.custom_restricted_item_code || [];

    const headers = [
        "item_code",
        "item_name"
    ];

    let data = [];


    // If child table has data, download existing data
    if (rows.length) {

        data = rows.map(row => ({
            item_code: row.item_code || "",
            item_name: row.item_name || ""
        }));

    }

    // If child table is empty, download sample row
    else {

        data = [
            {
                item_code: "ITEM-001",
                item_name: "Sample Item"
            }
        ];

    }


    // CSV Header
    let csv = headers.join(",") + "\n";


    // CSV Data
    data.forEach(row => {

        csv += headers.map(field => {

            const value = String(row[field] ?? "")
                .replace(/"/g, '""');

            return `"${value}"`;

        }).join(",") + "\n";

    });


    // Create CSV file
    const blob = new Blob(
        [csv],
        {
            type: "text/csv;charset=utf-8;"
        }
    );


    const url = URL.createObjectURL(blob);

    const link = document.createElement("a");

    link.href = url;

    link.download = rows.length
        ? "restricted_item_code.csv"
        : "restricted_item_code_template.csv";


    document.body.appendChild(link);

    link.click();

    document.body.removeChild(link);

    URL.revokeObjectURL(url);
}
/* =========================================================
   UPLOAD CSV AND ADD DATA TO CHILD TABLE
   ========================================================= */

function upload_restricted_item_code(frm) {

    // Create hidden file input
    const input = document.createElement("input");

    input.type = "file";
    input.accept = ".csv,text/csv";

    input.onchange = function (event) {

        const file = event.target.files[0];

        if (!file) {
            return;
        }

        const reader = new FileReader();

        reader.onload = function (e) {

            const csv_text = e.target.result;

            try {

                const rows = parse_csv(csv_text);

                if (!rows.length) {
                    frappe.msgprint({
                        title: __("No Data"),
                        message: __("No valid data found in the CSV file."),
                        indicator: "orange"
                    });

                    return;
                }


                let added_rows = 0;


                rows.forEach(row => {

                    // Skip empty rows
                    if (!row.item_code) {
                        return;
                    }


                    // Add child row
                    const child = frm.add_child(
                        "custom_restricted_item_code"
                    );


                    // Set Item Code
                    child.item_code = row.item_code;


                    // Set Item Name if available
                    if (row.item_name) {
                        child.item_name = row.item_name;
                    }


                    added_rows++;

                });


                // Refresh child table
                frm.refresh_field(
                    "custom_restricted_item_code"
                );


                frappe.show_alert({
                    message: __(
                        "{0} row(s) added successfully",
                        [added_rows]
                    ),
                    indicator: "green"
                });


                // Remove file input
                input.remove();

            } catch (error) {

                console.error(
                    "Restricted Item Code CSV Error:",
                    error
                );

                frappe.msgprint({
                    title: __("Upload Error"),
                    message: __(
                        "Could not read the CSV file. Please check the CSV format."
                    ),
                    indicator: "red"
                });

            }

        };


        reader.onerror = function () {

            frappe.msgprint({
                title: __("File Error"),
                message: __("Unable to read the selected file."),
                indicator: "red"
            });

        };


        // Read CSV
        reader.readAsText(file);

    };


    // Open file picker
    input.click();
}


/* =========================================================
   CSV PARSER
   ========================================================= */

function parse_csv(text) {

    const lines = [];
    let current = "";
    let inside_quotes = false;


    // Parse CSV character by character
    for (let i = 0; i < text.length; i++) {

        const char = text[i];
        const next_char = text[i + 1];


        // Handle quotes
        if (char === '"') {

            if (inside_quotes && next_char === '"') {

                current += '"';
                i++;

            } else {

                inside_quotes = !inside_quotes;

            }

        }


        // Handle new line
        else if (
            (char === "\n" || char === "\r") &&
            !inside_quotes
        ) {

            if (current.trim() !== "") {
                lines.push(current);
            }

            current = "";

            // Handle Windows \r\n
            if (
                char === "\r" &&
                next_char === "\n"
            ) {
                i++;
            }

        }


        else {

            current += char;

        }

    }


    // Last line
    if (current.trim() !== "") {
        lines.push(current);
    }


    if (!lines.length) {
        return [];
    }


    // First row = headers
    const headers = parse_csv_line(lines[0]);


    const data = [];


    for (let i = 1; i < lines.length; i++) {

        const values = parse_csv_line(lines[i]);

        if (!values.length) {
            continue;
        }


        const row = {};


        headers.forEach((header, index) => {

            row[header.trim()] =
                values[index] !== undefined
                    ? values[index].trim()
                    : "";

        });


        data.push(row);

    }


    return data;
}


/* =========================================================
   PARSE SINGLE CSV LINE
   ========================================================= */

function parse_csv_line(line) {

    const values = [];

    let current = "";
    let inside_quotes = false;


    for (let i = 0; i < line.length; i++) {

        const char = line[i];
        const next_char = line[i + 1];


        if (char === '"') {

            if (inside_quotes && next_char === '"') {

                current += '"';
                i++;

            } else {

                inside_quotes = !inside_quotes;

            }

        }


        else if (char === "," && !inside_quotes) {

            values.push(current);
            current = "";

        }


        else {

            current += char;

        }

    }


    values.push(current);


    return values;
}