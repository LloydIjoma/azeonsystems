import os
import glob
import frappe
from frappe.utils.backups import new_backup
import boto3
from botocore.exceptions import NoCredentialsError

def run_tenant_s3_backup(site_name=None):
    """
    Generates a full backup for a site and uploads SQL dumps and files to S3.
    """
    if not site_name:
        site_name = frappe.local.site

    frappe.init(site=site_name)
    frappe.connect()

    print(f"[*] Initiating backup for site: {site_name}")
    
    # Trigger native Frappe backup
    backup_obj = new_backup(ignore_files=False, backup_path_db=None)
    
    files_to_upload = {
        "database": backup_obj.backup_path_db,
        "public_files": backup_obj.backup_path_files,
        "private_files": backup_obj.backup_path_private_files,
        "site_config": backup_obj.backup_path_conf
    }

    # Fetch S3 Credentials from System Settings or Environment
    s3_bucket = frappe.conf.get("s3_backup_bucket") or os.environ.get("S3_BACKUP_BUCKET")
    aws_access_key = frappe.conf.get("aws_access_key_id") or os.environ.get("AWS_ACCESS_KEY_ID")
    aws_secret_key = frappe.conf.get("aws_secret_access_key") or os.environ.get("AWS_SECRET_ACCESS_KEY")
    aws_region = frappe.conf.get("aws_region") or os.environ.get("AWS_REGION", "us-east-1")

    if not all([s3_bucket, aws_access_key, aws_secret_key]):
        print("[!] S3 configuration missing in site_config.json or environment variables. Skipping upload.")
        return {"status": "local_only", "files": files_to_upload}

    s3_client = boto3.client(
        's3',
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
        region_name=aws_region
    )

    uploaded_keys = []
    for category, file_path in files_to_upload.items():
        if file_path and os.path.exists(file_path):
            file_name = os.path.basename(file_path)
            s3_key = f"backups/{site_name}/{category}/{file_name}"
            
            try:
                print(f"[*] Uploading {file_name} to s3://{s3_bucket}/{s3_key}...")
                s3_client.upload_file(file_path, s3_bucket, s3_key)
                uploaded_keys.append(s3_key)
            except Exception as e:
                print(f"[!] Failed to upload {file_name}: {str(e)}")

    frappe.destroy()
    return {"status": "success", "uploaded_keys": uploaded_keys}

def restore_tenant_from_s3(site_name, backup_timestamp, s3_bucket, aws_access_key, aws_secret_key, aws_region="us-east-1"):
    """
    Downloads backup files from S3 and restores a tenant site.
    """
    s3_client = boto3.client(
        's3',
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
        region_name=aws_region
    )

    download_dir = f"/tmp/restore_{site_name}"
    os.makedirs(download_dir, exist_ok=True)

    prefix = f"backups/{site_name}/"
    objects = s3_client.list_objects_v2(Bucket=s3_bucket, Prefix=prefix)

    db_file = None
    for obj in objects.get('Contents', []):
        key = obj['Key']
        if backup_timestamp in key:
            local_target = os.path.join(download_dir, os.path.basename(key))
            print(f"[*] Downloading {key} to {local_target}...")
            s3_client.download_file(s3_bucket, key, local_target)
            if key.endswith(".sql.gz"):
                db_file = local_target

    if db_file:
        print(f"[*] Restoring database from {db_file}...")
        os.system(f"bench --site {site_name} restore {db_file} --force")
        print("[+] Restoration process executed.")
    else:
        print("[!] No matching database backup file found for timestamp.")
