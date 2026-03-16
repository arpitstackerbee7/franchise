import frappe
from frappe import _


def check_session_limit(login_manager):

    user = frappe.form_dict.get("usr")

    if not user or user.lower() in ["administrator", "guest"]:
        return

    active_sessions = frappe.db.count("Sessions", {"user": user})

    if active_sessions > 0:

        html_msg = _(
        """
        This user id is already logged in.<br>
        Click
        <button type="button" class="btn btn-primary"
        onclick="
        var user=document.getElementById('login_email').value;
        var pass=document.getElementById('login_password').value;

        frappe.call({
            method:'franchise_erp.auth.force_logout_and_login',
            args:{user:user},
            callback:function(){
                fetch('/api/method/login',{
                    method:'POST',
                    headers:{'Content-Type':'application/json'},
                    body:JSON.stringify({usr:user,pwd:pass})
                }).then(r=>r.json()).then(()=>{
                    window.location='/app';
                });
            }
        });
        ">
        Login
        </button>
        to login again.
        <br>
        Please note, by clicking this your existing session will be automatically logged out without saving.
        """
        )

        frappe.throw(html_msg, frappe.AuthenticationError)


@frappe.whitelist(allow_guest=True)
def force_logout_and_login(user):

    # ERPNext built-in session clear
    frappe.sessions.clear_sessions(user)

    frappe.db.commit()

    return {"status": "success"}