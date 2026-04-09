# import frappe
# from math import radians, cos, sin, asin, sqrt

# def get_distance(lat1, lon1, lat2, lon2):
#     """Haversine formula to calculate distance in meters"""
#     try:
#         lat1, lon1, lat2, lon2 = map(float, [lat1, lon1, lat2, lon2])
#         lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
#         dlon = lon2 - lon1
#         dlat = lat2 - lat1
#         a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
#         c = 2 * asin(sqrt(a))
#         return 6371 * c * 1000 
#     except Exception:
#         return 999999

# @frappe.whitelist()
# def check_login_location(latitude, longitude):
#     user = frappe.session.user
#     if user == "Guest": return {"status": "success"}

#     user_setup = frappe.db.get_value("Counter Location", {"user": user}, 
#         ["location_name", "enable_location_restriction", "name"], as_dict=True)

#     if not user_setup or not user_setup.enable_location_restriction:
#         return {"status": "success"}

#     master_loc = frappe.db.get_value("Location", user_setup.location_name, 
#         ["latitude", "longitude", "custom_allow_radius_for_login"], as_dict=True)

#     if not master_loc or not master_loc.latitude:
#         return {"status": "success"}

#     distance = get_distance(latitude, longitude, master_loc.latitude, master_loc.longitude)
#     allowed_radius = float(master_loc.custom_allow_radius_for_login or 100)

#     frappe.log_error(
#         message=f"User: {user}\nBrowser GPS: {latitude}, {longitude}\nMaster GPS: {master_loc.latitude}, {master_loc.longitude}\nDistance: {round(distance)}m\nAllowed: {allowed_radius}m",
#         title="Location Security Check"
#     )

#     if distance > allowed_radius:
#         frappe.local.login_manager.logout()
#         frappe.db.commit()
        
#         dist_text = f"{round(distance)}m" if distance < 1000 else f"{round(distance/1000, 2)}km"
#         return {
#             "status": "failed",
#             "message": f"❌ <b>Access Blocked</b><br>You are {dist_text} away from your office. Allowed radius: {allowed_radius}m."
#         }

#     frappe.db.set_value("Counter Location", user_setup.name, "last_login_location", f"{latitude}, {longitude}", update_modified=False)
#     frappe.db.commit()
#     return {"status": "success"}