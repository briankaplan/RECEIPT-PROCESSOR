import boto3
import os
import logging
import mimetypes
from pathlib import Path
from botocore.exceptions import ClientError, BotoCoreError
import time

def upload_receipts(r2_config, receipt_paths, max_retries=3):
    """
    Upload a list of receipt files to R2 with public access.
    Returns a dict: {'success': [...], 'failed': [...], 'urls': {local_path: public_url}}
    """
    s3 = boto3.client(
        "s3",
        endpoint_url=r2_config["endpoint"],
        aws_access_key_id=r2_config["access_key"],
        aws_secret_access_key=r2_config["secret_key"]
    )

    uploaded_urls = {}
    successes = []
    failures = []

    for local_path in receipt_paths:
        file_path = Path(local_path)

        if not file_path.exists():
            logging.warning(f"⚠️ File not found: {file_path}")
            failures.append(str(file_path))
            continue

        key = file_path.name
        bucket = r2_config["bucket"]

        mime_type, _ = mimetypes.guess_type(str(file_path))
        extra_args = {"ACL": "public-read"}
        if mime_type:
            extra_args["ContentType"] = mime_type

        for attempt in range(1, max_retries + 1):
            try:
                s3.upload_file(
                    Filename=str(file_path),
                    Bucket=bucket,
                    Key=key,
                    ExtraArgs=extra_args
                )

                public_url = f"{r2_config['public_url'].rstrip('/')}/{key}"
                uploaded_urls[str(file_path)] = public_url
                successes.append(str(file_path))
                logging.info(f"✅ Uploaded {file_path} → {public_url}")
                break

            except (ClientError, BotoCoreError) as e:
                logging.warning(f"⚠️ Attempt {attempt} failed for {file_path}: {e}")
                time.sleep(2 ** attempt)  # Backoff

        else:
            logging.error(f"❌ Giving up on {file_path} after {max_retries} retries")
            failures.append(str(file_path))

    return {
        "success": successes,
        "failed": failures,
        "urls": uploaded_urls
    }