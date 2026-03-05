frappe.listview_settings["Delivery Note"] = {

    onload: function(listview) {

        let serial_filter_applied = false;

        setTimeout(() => {

            let filter_row = $(".standard-filter-section");

            if (!filter_row.length) return;

            if (filter_row.find('[data-fieldname="serial_no_custom"]').length) return;

            let serial_field = $(`
                <div class="form-group frappe-control input-max-width col-md-2"
                     data-fieldtype="Data"
                     data-fieldname="serial_no_custom">

                    <input type="text"
                        autocomplete="off"
                        class="input-with-feedback form-control input-xs"
                        placeholder="Serial No">

                </div>
            `);

            filter_row.append(serial_field);

            serial_field.find("input").on("input", frappe.utils.debounce(function() {

                let serial = $(this).val();

                // ✅ If empty → remove only ID filter
                if (!serial) {
                    full_reset(listview);
                    return;
                }

                frappe.call({
                    method: "franchise_erp.custom.delivery_note.get_delivery_note_by_serial",
                    args: { serial: serial },
                    callback: function(r) {

                        // Always remove old ID filter first
                        full_reset(listview);

                        if (r.message && r.message.length) {

                            listview.filter_area.add([
                                ["Delivery Note", "name", "in", r.message]
                            ]);

                        } else {

                            // Show empty list WITHOUT fake filter
                            listview.data = [];
                            listview.render();
                            return;

                        }

                        listview.refresh();
                    }
                });

            }, 500));
        }, 700);

    }
};

function full_reset(listview) {

    // 1️⃣ Clear all filters
    listview.filter_area.clear();

    // 2️⃣ Clear route (removes ?name= etc)
    frappe.set_route("List", "Delivery Note");

    // 3️⃣ Reset filter badge count manually (safety)
    listview.page.clear_indicator();

    listview.filter_area.remove();

    // 4️⃣ Reload full list properly
    setTimeout(() => {
        listview.refresh();
    }, 200);
}