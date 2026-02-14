console.log("--- Tejoo Uploader Patch V2 Loaded ---");
/* Default file uploader to public mode */
$(document).ready(function() {
    if (frappe.ui.FileUploader) {
        const OriginalUploader = frappe.ui.FileUploader;

        frappe.ui.FileUploader = class extends OriginalUploader {
            constructor(opts) {
                opts = opts || {};
				// Force public mode for both Vue and Standard versions
                opts.make_attachments_public = true; 
                opts.is_private = 0;
                
                super(opts);
                console.log("Setting default to Public");
            }
        };
    }
});