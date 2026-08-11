import time
import frappe
from frappe.utils.background_jobs import get_jobs


def pause_jobs_before_migrate():
    
    frappe.utils.scheduler.disable_scheduler()
    frappe.db.commit()

    
    site = frappe.local.site
    max_wait_seconds = 120
    waited = 0
    while waited < max_wait_seconds:
        running = get_jobs(site=site, key="job_name").get(site, [])
        if not running:
            break
        time.sleep(5)
        waited += 5


def resume_jobs_after_migrate():
    
    frappe.utils.scheduler.enable_scheduler()
    frappe.db.commit()