// frappe.provide("frappe.ui.form");

// console.log("🧩 Customer Quick Entry Patch Loaded");

// (function () {
//     const original_make_quick_entry = frappe.ui.form.make_quick_entry;

//     frappe.ui.form.make_quick_entry = function (...args) {
//         console.log("⚡ make_quick_entry called");

//         return frappe
//             .require("/assets/franchise_erp/js/customer_quick_entry.js")
//             .then(() => {
//                 console.log("✅ customer_quick_entry.js loaded");
//                 return original_make_quick_entry.apply(this, args);
//             });
//     };
// })();
