
frappe.listview_settings["Advance e-Waybill Log"] = {
    onload(listview) {
        listview.page.add_inner_button(
            __("Import GST E-Way Bill"),
            () => {
                const input = document.createElement("input");
                input.type = "file";
                input.accept = ".xls,.html,.htm";
                input.style.display = "none";

                input.addEventListener("change", async () => {
                    const file = input.files[0];
                    if (!file) {
                        input.remove();
                        return;
                    }

                    const formData = new FormData();
                    formData.append("file", file);

                    frappe.show_alert({
                        message: __("Uploading and importing file..."),
                        indicator: "blue"
                    });

                    try {
                        const response = await fetch(
                            "/api/method/franchise_erp.ewaybill_import.import_ewaybill_html_xls",
                            {
                                method: "POST",
                                body: formData,
                                headers: {
                                    "X-Frappe-CSRF-Token": frappe.csrf_token
                                },
                                credentials: "same-origin"
                            }
                        );

                        const result = await response.json();

                        if (!response.ok || result.exc) {
                            throw new Error(
                                result._server_messages
                                    ? JSON.parse(result._server_messages)
                                        .map(msg => {
                                            try {
                                                return JSON.parse(msg).message;
                                            } catch {
                                                return msg;
                                            }
                                        }).join("\n")
                                    : (result.exception || "Import failed")
                            );
                        }

                        const data = result.message || {};

                        frappe.msgprint({
                            title: __("E-Way Bill Import Result"),
                            indicator: data.failed ? "orange" : "green",
                            message: `
                                <p><b>Inserted:</b> ${data.inserted || 0}</p>
                                <p><b>Duplicates skipped:</b> ${data.skipped_duplicates || 0}</p>
                                <p><b>Failed:</b> ${data.failed || 0}</p>
                                ${
                                    data.errors && data.errors.length
                                        ? `<pre style="white-space:pre-wrap;max-height:300px;overflow:auto">${frappe.utils.escape_html(
                                            JSON.stringify(data.errors, null, 2)
                                        )}</pre>`
                                        : ""
                                }
                            `
                        });

                        listview.refresh();

                    } catch (error) {
                        frappe.msgprint({
                            title: __("Import Failed"),
                            indicator: "red",
                            message: frappe.utils.escape_html(
                                error.message || String(error)
                            )
                        });
                    } finally {
                        input.remove();
                    }
                });

                document.body.appendChild(input);
                input.click();
            }
        );
    }
};