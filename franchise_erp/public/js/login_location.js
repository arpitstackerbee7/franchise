// $(document).ready(function () {
//     const current_path = window.location.pathname;

//     // LOGIN PAGE LOGIC
//     if (current_path.indexOf('/login') !== -1) {
//         const urlParams = new URLSearchParams(window.location.search);
//         const msg = urlParams.get('error_msg');
        
//         if (msg) {
//             // Wait 500ms for Frappe UI to be ready
//             setTimeout(function() {
//                 frappe.msgprint({
//                     title: __('Access Denied'),
//                     indicator: 'red',
//                     message: decodeURIComponent(msg)
//                 });
//             }, 500);

//             // Clean URL
//             const clean_url = window.location.protocol + "//" + window.location.host + current_path;
//             window.history.replaceState({}, document.title, clean_url);
//         }
//         return; 
//     }

//     // DESK (APP) LOGIC
//     if (!window.frappe || !frappe.session || frappe.session.user === "Guest") return;
//     if (!current_path.startsWith('/app')) return;

//     const overlay = $('<div id="sec-overlay" style="position:fixed; top:0; left:0; width:100%; height:100%; background:white; z-index:999999; display:flex; align-items:center; justify-content:center; flex-direction:column; font-family:sans-serif;">' +
//         '<div style="text-align:center;">' +
//         '<div class="spinner-border text-primary" style="width: 3rem; height: 3rem;"></div>' +
//         '<h2 style="margin-top:20px; color:#333;">🔒 Verifying Security...</h2>' +
//         '<p style="color:#666;">Checking location access, please wait.</p>' +
//         '</div></div>').appendTo('body');

//     if (navigator.geolocation) {
//         navigator.geolocation.getCurrentPosition(
//             function (position) {
//                 frappe.call({
//                     method: "franchise_erp.login_location.check_login_location",
//                     args: {
//                         latitude: position.coords.latitude,
//                         longitude: position.coords.longitude
//                     },
//                     callback: function (r) {
//                         if (r.message && r.message.status === "failed") {
//                             window.location.replace("/login?error_msg=" + encodeURIComponent(r.message.message));
//                         } else {
//                             overlay.fadeOut(400, function() { $(this).remove(); });
//                         }
//                     },
//                     error: function() {
//                         window.location.replace("/login");
//                     }
//                 });
//             },
//             function (error) {
//                 window.location.replace("/login?error_msg=Location access is required for security.");
//             },
//             { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
//         );
//     } else {
//         window.location.replace("/login?error_msg=Browser does not support GPS.");
//     }
    
// });

