import os
import frappe

def get_dir_size(path):
    total = 0
    if not os.path.exists(path):
        return 0
    for root, _, files in os.walk(path):
        for f in files:
            fp = os.path.join(root, f)
            if not os.path.islink(fp):
                total += os.path.getsize(fp)
    return total

@frappe.whitelist()
def collect_site_metrics():
    """
    Gathers storage, user, and API metrics for the current site.
    """
    site_path = frappe.get_site_path()
    
    # 1. File Storage Usage (public + private files)
    files_path = os.path.join(site_path, "public", "files")
    private_files_path = os.path.join(site_path, "private", "files")
    
    total_file_bytes = get_dir_size(files_path) + get_dir_size(private_files_path)
    total_file_mb = round(total_file_bytes / (1024 * 1024), 2)

    # 2. Database Size Calculation
    db_size_bytes = frappe.db.sql("""
        SELECT SUM(data_length + index_length) 
        FROM information_schema.tables 
        WHERE table_schema = DATABASE()
    """)[0][0] or 0
    db_size_mb = round(db_size_bytes / (1024 * 1024), 2)

    # 3. Active Users Count (excluding System Users/Guest)
    active_users = frappe.db.count("User", {
        "enabled": 1,
        "user_type": "System User",
        "name": ["not in", ["Administrator", "Guest"]]
    })

    # 4. Monthly API Call Volume (from Activity Log)
    api_calls_this_month = frappe.db.count("Activity Log", {
        "creation": [">=", frappe.utils.now_datetime().replace(day=1, hour=0, minute=0, second=0)],
        "operation": "login"
    })

    metrics = {
        "site": frappe.local.site,
        "db_size_mb": db_size_mb,
        "file_storage_mb": total_file_mb,
        "total_storage_mb": round(db_size_mb + total_file_mb, 2),
        "active_users": active_users,
        "monthly_activity_logs": api_calls_this_month
    }

    return metrics
