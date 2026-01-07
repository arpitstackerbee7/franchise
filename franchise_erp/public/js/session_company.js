(function () {
    "use strict";

    function renderCompanyBadge() {
        // 1. Company name Global Defaults se nikalna
        const company = frappe.defaults.get_default("default_company") || 
                        frappe.defaults.get_default("company") || 
                        (frappe.boot && frappe.boot.sysdefaults.company);

        if (!company) {
            return;
        }

        // Duplicate badge check
        if (document.getElementById("company-navbar-badge")) return;

        // 2. Navbar Search Bar ko target karna (v14/v15 standard)
        const searchContainer = document.querySelector(".search-bar, .navbar-search, .awesome-bar");
        
        if (searchContainer) {
            const badge = document.createElement("div");
            badge.id = "company-navbar-badge";
            
            // CSS for Badge (Awesomebar ke left mein fit hone ke liye)
            badge.style.cssText = `
                display: flex;
                align-items: center;
                margin-right: 15px;
                padding: 0px 12px;
                background-color: #f3f4f6;
                border: 1px solid #d1d5db;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 700;
                color: #1f2937;
                height: 28px;
                white-space: nowrap;
                align-self: center;
                pointer-events: none;
            `;
            
            badge.innerHTML = `<span style="margin-left: 5px;">${company}</span>`;

            // Search bar ke parent container mein sabse pehle (Left side) add karna
            searchContainer.parentElement.insertBefore(badge, searchContainer);
            console.log("✅ Badge added: " + company);
        }
    }

    // Frappe Desk load hone ka wait karne ke liye setInterval sabse best hai
    let retryCount = 0;
    const checkExist = setInterval(function() {
        if (window.frappe && document.querySelector(".navbar-search, .search-bar")) {
            renderCompanyBadge();
            // 10 baar try karega jab tak mil na jaye
            if (document.getElementById("company-navbar-badge") || retryCount > 10) {
                clearInterval(checkExist);
            }
        }
        retryCount++;
    }, 500);

    // Route change hone par dobara check karein
    $(document).on("app_ready page-change", function() {
        setTimeout(renderCompanyBadge, 500);
    });

})();