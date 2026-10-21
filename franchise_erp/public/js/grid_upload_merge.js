(function () {
    if (window.pflCustomUploadInstalled) return;
    window.pflCustomUploadInstalled = true;

    frappe.ui.form.on("Promotion Franchise linking", {
        refresh(frm) {
            const grid = frm.fields_dict.franchises?.grid;
            if (!grid) return;

            const wrapper = $(grid.wrapper);
            let holder = wrapper.find(".grid-bulk-actions").first();

            if (!holder.length) {
                holder = wrapper;
            }

            holder.find(".pfl-custom-actions").remove();

            const actions = $(`
                <div class="pfl-custom-actions"
                     style="display:flex;justify-content:flex-end;
                     gap:8px;margin:8px 0;">
                    <button type="button"
                        class="btn btn-xs btn-secondary">
                        Download CSV
                    </button>
                    <button type="button"
                        class="btn btn-xs btn-primary">
                        Upload CSV
                    </button>
                </div>
            `);

            holder.append(actions);

            const downloadBtn = actions.find("button").eq(0);
            const uploadBtn = actions.find("button").eq(1);

            // CUSTOM DOWNLOAD
            downloadBtn.on("click", function () {
                const rows = frm.doc.franchises || [];

                function escapeCsv(value) {
                    const text = String(value ?? "");
                    return '"' + text.replace(/"/g, '""') + '"';
                }

                const csv = [
                    ["franchise", "disable"],
                    ...rows.map(row => [
                        row.franchise || "",
                        row.disable ? 1 : 0
                    ])
                ].map(row => row.map(escapeCsv).join(",")).join("\r\n");

                const blob = new Blob(
                    ["\uFEFF" + csv],
                    { type: "text/csv;charset=utf-8;" }
                );

                const url = URL.createObjectURL(blob);
                const link = document.createElement("a");

                link.href = url;
                link.download = "promotion_franchises.csv";
                document.body.appendChild(link);
                link.click();
                link.remove();
                URL.revokeObjectURL(url);
            });

            // CUSTOM UPLOAD
            uploadBtn.on("click", function () {
new frappe.ui.FileUploader({
                    as_dataurl: true,
                    allow_multiple: false,
                    restrictions: {
                        allowed_file_types: [".csv"]
                    },

                    on_success(file) {
                        let data;

                        try {
                            data = frappe.utils.csv_to_array(
                                frappe.utils.get_decoded_string(file.dataurl)
                            );
                        } catch (e) {
                            frappe.msgprint(__("Unable to read CSV file."));
                            return;
                        }

                        if (!data.length) {
                            frappe.msgprint(__("CSV file is empty."));
                            return;
                        }

                        // Support both simple CSV and default Frappe Bulk Edit CSV.
                        const normalize = row => (row || []).map(v =>
                            String(v ?? "").replace(/^\uFEFF/, "").trim().toLowerCase()
                        );

                        let headers = normalize(data[0]);
                        let dataStart = 1;

                        if (!headers.includes("franchise")) {
                            headers = normalize(data[2]);
                            dataStart = 7;
                        }

                        const franchiseIndex = headers.indexOf("franchise");
                        const disableIndex = headers.indexOf("disable");

                        if (franchiseIndex < 0) {
                            frappe.msgprint(
                                __("Could not find the franchise field. Please use the default Bulk Edit CSV template.")
                            );
                            return;
                        }

                        const csvRows = data.slice(dataStart);

                        if (csvRows.length > 5000) {
                            frappe.msgprint(__("Cannot import more than 5000 rows."));
                            return;
                        }

                        const rows = csvRows
                            .filter(row => row && String(row[franchiseIndex] || "").trim())
                            .map(row => ({
                                franchise: String(row[franchiseIndex] || "").trim(),
                                disable: disableIndex >= 0 ? row[disableIndex] : 0
                            }));

                        if (!rows.length) {
                            frappe.msgprint(__("No franchise rows found in the CSV."));
                            return;
                        }

                        // For a new document, merge rows locally.
// The parent document can be saved normally afterward.
if (frm.is_new()) {
    const existing = new Set(
        (frm.doc.franchises || [])
            .map(row => String(row.franchise || "").trim().toLowerCase())
            .filter(Boolean)
    );

    let added = 0;
    let skipped = 0;

    rows.forEach(item => {
        const franchise = item.franchise.trim();
        const key = franchise.toLowerCase();

        if (existing.has(key)) {
            skipped++;
            return;
        }

        const child = frm.add_child("franchises");
        child.franchise = franchise;

        const disableValue = String(item.disable ?? "0")
            .trim()
            .toLowerCase();

        child.disable = ["1", "true", "yes", "on"].includes(disableValue)
            ? 1
            : 0;

        existing.add(key);
        added++;
    });

    frm.refresh_field("franchises");

    frappe.msgprint({
        title: __("Upload Complete"),
        indicator: "green",
        message: __(
            "Added {0} new franchise(s). Skipped {1} duplicate(s). Save the document to persist the changes.",
            [added, skipped]
        )
    });

    return;
}

// Existing saved document: use the server-side merge API.
frappe.call({
    method: "franchise_erp.overrides.promotion_franchise_linking.merge_franchises_upload",
    args: {
        docname: frm.doc.name,
        rows: JSON.stringify(rows)
    },
    freeze: true,
    freeze_message: __("Merging franchises..."),

    callback(r) {
        if (r.exc || !r.message) return;

        const result = r.message;

        frm.reload_doc().then(() => {
            frappe.msgprint({
                title: __("Upload Complete"),
                indicator: "green",
                message: __(
                    "Added {0} new franchise(s). Skipped {1} duplicate(s). Existing rows retained.",
                    [result.added, result.skipped]
                )
            });
        });
    }
});
                    }
                });
            });
        }
    });
})();
