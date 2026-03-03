// frappe.listview_settings["Sales Invoice"] = {

//     onload: function(listview) {

//         // Add filter inside default filter row
//         listview.page.add_inner_button("Serial No Filter", function() {

//             frappe.prompt(
//                 [
//                     {
//                         label: "Enter Serial No",
//                         fieldname: "serial_no",
//                         fieldtype: "Data",
//                         reqd: 1
//                     }
//                 ],
//                 function(values) {

//                     frappe.call({
//                         method: "franchise_erp.custom.sales_invoice.get_sales_invoice_by_serial",
//                         args: {
//                             serial: values.serial_no
//                         },
//                         callback: function(r) {

//                             listview.filter_area.clear();

//                             if (r.message && r.message.length) {

//                                 listview.filter_area.add([
//                                     ["Sales Invoice", "name", "in", r.message]
//                                 ]);

//                                 listview.refresh();
//                             }
//                             else {
//                                 listview.refresh();
//                                 frappe.msgprint("Serial Not Found");
//                             }
//                         }
//                     });

//                 },
//                 "Serial Search",
//                 "Search"
//             );

//         });

//     }
// };

frappe.listview_settings["Sales Invoice"] = {

    onload: function(listview) {

        // Wait until standard filters render
        setTimeout(() => {

            let filter_row = $(".standard-filter-section");

            if (!filter_row.length) return;

            // Prevent duplicate
            if (filter_row.find('[data-fieldname="serial_no_custom"]').length) return;

            // Create same style filter field
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

            // Append inside same row
            filter_row.append(serial_field);

            // Auto search on paste / typing
            serial_field.find("input").on("input", frappe.utils.debounce(function() {

                let serial = $(this).val();

                if (!serial) {
                    listview.filter_area.clear();
                    listview.refresh();
                    return;
                }

                frappe.call({
                    method: "franchise_erp.custom.sales_invoice.get_sales_invoice_by_serial",
                    args: { serial: serial },
                    callback: function(r) {

                        listview.filter_area.clear();

                        if (r.message && r.message.length) {

                            listview.filter_area.add([
                                ["Sales Invoice", "name", "in", r.message]
                            ]);

                        } else {
                            frappe.msgprint("Serial Not Found");
                        }

                        listview.refresh();
                    }
                });

            }, 500));

        }, 700);

    }
};