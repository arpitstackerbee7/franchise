console.log("LOGIN JS LOADED");

setTimeout(() => {

    frappe.call({
        method: "franchise_erp.api.is_otp_login_enabled",
        callback: function(r) {

            if (!r.message) {
                console.log("OTP Login Disabled");
                return;
            }

            if ($("#mobile-otp-login").length) {
                return;
            }

            const otp_btn = $(`
    <div class="mt-3">
        <button
            class="btn btn-sm btn-primary btn-block btn-login"
            id="mobile-otp-login"
            type="button">
            Login with Mobile OTP
        </button>
    </div>
`);

console.log("OTP Login Enabled");
console.log("Page Card Count:", $(".page-card-body").length);

$(".page-card-body").first().append(otp_btn);
        }
    });

}, 1000);
function start_otp_timer() {
    console.log("TIMER STARTED");
clearInterval(window.otp_timer);
    let seconds = 301;

    window.otp_timer = setInterval(function () {

        let min = Math.floor(seconds / 60);
        let sec = seconds % 60;

        $("#otp-timer").text(
            `OTP expires in ${min}:${sec.toString().padStart(2, "0")}`
        );

        seconds--;

        if (seconds < 0) {

            clearInterval(window.otp_timer);

            $("#otp-timer").text("OTP Expired");

            $("#resend-otp-btn").show();
        }

    }, 1000);
}
$(document).on("click", "#mobile-otp-login", function () {

    if ($("#otp-login-modal").length) {
        $("#otp-login-modal").modal("show");
        return;
    }

    $("body").append(`
        <div class="modal fade" id="otp-login-modal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">

                    <div class="modal-header">
                        <h5 class="modal-title">Mobile OTP Login</h5>
                        <button type="button" class="close" data-dismiss="modal">
                            <span>&times;</span>
                        </button>
                    </div>

                    <div class="modal-body">
                        <div class="form-group">
                            <label>
    Mobile Number
    <span style="color:red">*</span>
</label>
                            <input
                                type="text"
                                id="otp-mobile-number"
                                class="form-control"
                                placeholder="Enter Mobile Number">
                        </div>
                    </div>

                    <div class="modal-footer">
                        <button
                            type="button"
                            class="btn btn-primary"
                            id="send-otp-btn">
                            Send OTP
                        </button>
                    </div>

                </div>
            </div>
        </div>
    `);

    $("#otp-login-modal").modal("show");
});


$(document).on("click", "#send-otp-btn", function () {

    const mobile = $("#otp-mobile-number").val().trim();

    if (!mobile) {
        frappe.msgprint("Please enter Mobile Number");
        return;
    }

    frappe.call({
        method: "franchise_erp.api.send_mobile_otp",
        args: {
            mobile_no: mobile
        },
        callback: function(r) {

    console.log(r);

    if (r.message && r.message.success) {

        $("#otp-login-modal .modal-body").html(`
    <div id="otp-timer"
        style="
            color:red;
            font-weight:bold;
            margin-bottom:10px;
        ">
    </div>

    <div class="form-group">
        <label>Enter OTP</label>
        <input
            type="text"
            id="entered-otp"
            class="form-control"
            placeholder="Enter OTP">
    </div>

        `);

        $("#otp-login-modal .modal-footer").html(`
    <button
        type="button"
        class="btn btn-success"
        id="verify-otp-btn"
        data-mobile="${mobile}">
        Verify OTP
    </button>

    <button
        type="button"
        class="btn btn-warning"
        id="resend-otp-btn"
        data-mobile="${mobile}"
        style="display:none;">
        Resend OTP
    </button>
`);
start_otp_timer();

        } else {

        frappe.msgprint({
    title: "Error",
    message: r.message?.message || "Failed to send OTP",
    indicator: "red"
});

    }

        }
    });

});

$(document).on("click", "#verify-otp-btn", function () {

    const mobile = $(this).data("mobile");
    const otp = $("#entered-otp").val().trim();

    if (!otp) {
        frappe.msgprint("Please enter OTP");
        return;
    }

    frappe.call({
        method: "franchise_erp.api.verify_mobile_otp",
        args: {
            mobile_no: mobile,
            otp: otp
        },
        callback: function(r) {

            if (r.message && r.message.success) {

                $("#otp-login-modal").modal("hide");

                window.location.href = "/app";

            } else {

                frappe.msgprint({
                title: "Error",
                message:
               (r.message && r.message.message)
              ? r.message.message
            : "Failed to send OTP",
               indicator: "red"
         });

            }

        }
    });

});
$(document).on("click", "#resend-otp-btn", function () {

    const mobile = $(this).data("mobile");

    frappe.call({
        method: "franchise_erp.api.send_mobile_otp",
        args: {
            mobile_no: mobile
        },
        callback: function(r) {

      if (r.message && r.message.success) {

    clearInterval(window.otp_timer);

    $("#resend-otp-btn").hide();

    frappe.show_alert({
        message: "New OTP Sent",
        indicator: "green"
    });

    start_otp_timer();
}
          
        }
    });

});
