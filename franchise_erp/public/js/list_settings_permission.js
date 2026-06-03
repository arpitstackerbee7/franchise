frappe.router.on("change", () => {

    function toggle_list_settings() {

        setTimeout(() => {

            const has_access = frappe.user_roles.includes("List Settings Manager");

            $(".dropdown-item").each(function () {

                const text = $(this).text().trim();

                if (text === "List Settings") {

                    if (has_access) {
                        $(this).show();
                    } else {
                        $(this).hide();
                    }
                }
            });

        }, 500);
    }

    toggle_list_settings();

    $(document).off("click.list_settings");

    $(document).on(
        "click.list_settings",
        ".menu-btn-group .dropdown-toggle",
        function () {
            toggle_list_settings();
        }
    );
});