frappe.ui.form.on("Module Profile", {
    refresh(frm) {
        render_module_profile(frm);
    }
});

function render_module_profile(frm) {

    const field = frm.get_field("module_html");

    if (!field) {
        return;
    }

    frm.set_df_property("module_html", "hidden", 0);

    let modules = frm.doc.__onload?.all_modules || [];

    if (!modules.length) {
        field.$wrapper.html(
            // `<div class="text-muted">
            //     ${__("No modules found")}
            // </div>`
        );
        return;
    }

    modules = [...new Set(modules)].sort();

    const blocked_modules = new Set(
        (frm.doc.block_modules || [])
            .map(row => row.module)
            .filter(Boolean)
    );

    const wrapper = field.$wrapper;

    wrapper.empty();

    const buttons = $(`
        <div style="margin-bottom: 15px;">
            <button class="btn btn-default btn-xs module-select-all">
                ${__("Select All")}
            </button>

            <button class="btn btn-default btn-xs module-unselect-all"
                    style="margin-left: 8px;">
                ${__("Unselect All")}
            </button>
        </div>
    `);

    wrapper.append(buttons);

    const container = $(`
        <div class="module-list"></div>
    `);

    container.css({
        display: "grid",
        gridTemplateColumns: "repeat(3, 1fr)",
        columnGap: "40px"
    });

    wrapper.append(container);

    // Modules
    modules.forEach(module => {

        const checked = !blocked_modules.has(module);

        const row = $(`
            <div style="">
                <label style="font-weight: normal; cursor: pointer;">
                    <input
                        type="checkbox"
                        class="module-checkbox"
                        data-module="${encodeURIComponent(module)}"
                        ${checked ? "checked" : ""}
                    >

                    <span style="margin-left: 5px;">
                        ${frappe.utils.escape_html(module)}
                    </span>
                </label>
            </div>
        `);

        container.append(row);
    });

    container.on("change", ".module-checkbox", function () {

        const module = decodeURIComponent(
            $(this).attr("data-module")
        );

        if (this.checked) {

            (frm.doc.block_modules || [])
                .filter(row => row.module === module)
                .forEach(row => {

                    frappe.model.clear_doc(
                        row.doctype,
                        row.name
                    );

                });

        } else {


            const already_blocked =
                (frm.doc.block_modules || [])
                    .some(row => row.module === module);

            if (!already_blocked) {

                frm.add_child("block_modules", {
                    module: module
                });

            }
        }

        frm.refresh_field("block_modules");
        frm.dirty();
    });

    buttons.find(".module-select-all").on("click", function () {

        (frm.doc.block_modules || [])
            .slice()
            .forEach(row => {

                frappe.model.clear_doc(
                    row.doctype,
                    row.name
                );

            });

        frm.refresh_field("block_modules");
        frm.dirty();

        render_module_profile(frm);
    });

    buttons.find(".module-unselect-all").on("click", function () {

        (frm.doc.block_modules || [])
            .slice()
            .forEach(row => {

                frappe.model.clear_doc(
                    row.doctype,
                    row.name
                );

            });

        modules.forEach(module => {

            frm.add_child("block_modules", {
                module: module
            });

        });

        frm.refresh_field("block_modules");
        frm.dirty();

        render_module_profile(frm);
    });
}