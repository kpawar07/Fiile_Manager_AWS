import json
import os
import uuid
import re
from datetime import datetime, timezone
from urllib.parse import unquote

import boto3
from botocore.exceptions import ClientError

REGION = os.environ["AWS_REGION"]
BUCKET = os.environ["BUCKET_NAME"]
TABLE_NAME = os.environ["TABLE_NAME"]

s3 = boto3.client("s3", region_name=REGION)
table = boto3.resource("dynamodb", region_name=REGION).Table(TABLE_NAME)

CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "http://localhost:5173"),
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "GET,POST,DELETE,OPTIONS"
}

def response(status, payload):
    return {
        "statusCode": status,
        "headers": CORS_HEADERS,
        "body": json.dumps(payload, default=str)
    }

def body_json(event):
    raw = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        import base64
        raw = base64.b64decode(raw).decode("utf-8")
    return json.loads(raw)

def query_params(event):
    return event.get("queryStringParameters") or {}

def clean_filename(name):
    # Keep only a safe display filename; S3 keys use a generated UUID.
    name = unquote(str(name or "file"))
    name = name.replace("\\", "/").split("/")[-1]
    name = re.sub(r"[^A-Za-z0-9._ ()-]", "_", name).strip(" .")
    return (name or "file")[:180]

def handler(event, context):
    method = (
        event.get("requestContext", {}).get("http", {}).get("method")
        or event.get("httpMethod", "GET")
    ).upper()
    path = event.get("rawPath") or event.get("path") or "/"

    if method == "OPTIONS":
        return response(200, {"ok": True})

    try:
        if method == "POST" and path.endswith("/upload-url"):
            data = body_json(event)
            filename = clean_filename(data.get("fileName"))
            content_type = str(data.get("contentType") or "application/octet-stream")[:150]
            size = int(data.get("fileSize") or 0)
            if size < 1 or size > 10 * 1024 * 1024:
                return response(400, {"error": "Choose a file between 1 byte and 10 MB for this demo."})

            file_id = str(uuid.uuid4())
            extension = filename.rsplit(".", 1)[-1] if "." in filename else "bin"
            key = f"uploads/{file_id}.{re.sub(r'[^A-Za-z0-9]', '', extension)[:12]}"
            url = s3.generate_presigned_url(
                "put_object",
                Params={"Bucket": BUCKET, "Key": key, "ContentType": content_type},
                ExpiresIn=300
            )
            return response(200, {
                "fileId": file_id, "s3Key": key, "fileName": filename,
                "contentType": content_type, "fileSize": size, "uploadUrl": url
            })

        if method == "POST" and path.endswith("/confirm-upload"):
            data = body_json(event)
            file_id, key = str(data.get("fileId", "")), str(data.get("s3Key", ""))
            if not file_id or not key.startswith("uploads/"):
                return response(400, {"error": "Invalid file details."})
            try:
                obj = s3.head_object(Bucket=BUCKET, Key=key)
            except ClientError:
                return response(400, {"error": "Upload was not found in S3."})
            item = {
                "fileId": file_id,
                "s3Key": key,
                "fileName": clean_filename(data.get("fileName")),
                "contentType": str(data.get("contentType") or obj.get("ContentType") or "application/octet-stream"),
                "fileSize": int(obj.get("ContentLength", data.get("fileSize", 0))),
                "uploadedAt": datetime.now(timezone.utc).isoformat(),
                "isDeleted": False
            }
            table.put_item(Item=item)
            return response(201, {"message": "Upload saved.", "file": item})

        if method == "GET" and path.endswith("/files"):
            result = table.scan()
            items = [i for i in result.get("Items", []) if not i.get("isDeleted", False)]
            while result.get("LastEvaluatedKey"):
                result = table.scan(ExclusiveStartKey=result["LastEvaluatedKey"])
                items.extend([i for i in result.get("Items", []) if not i.get("isDeleted", False)])
            items.sort(key=lambda x: x.get("uploadedAt", ""), reverse=True)
            return response(200, {"files": items})

        if method == "GET" and path.endswith("/download-url"):
            file_id = query_params(event).get("fileId")
            item = table.get_item(Key={"fileId": str(file_id or "")}).get("Item")
            if not item or item.get("isDeleted", False):
                return response(404, {"error": "File not found."})
            url = s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": BUCKET, "Key": item["s3Key"],
                        "ResponseContentDisposition": f'attachment; filename="{item["fileName"]}"'},
                ExpiresIn=300
            )
            return response(200, {"downloadUrl": url})

        if method == "DELETE" and path.endswith("/files"):
            file_id = query_params(event).get("fileId")
            item = table.get_item(Key={"fileId": str(file_id or "")}).get("Item")
            if not item or item.get("isDeleted", False):
                return response(404, {"error": "File not found."})
            # With S3 versioning enabled, this creates a delete marker.
            s3.delete_object(Bucket=BUCKET, Key=item["s3Key"])
            table.update_item(
                Key={"fileId": item["fileId"]},
                UpdateExpression="SET isDeleted = :d",
                ExpressionAttributeValues={":d": True}
            )
            return response(200, {"message": "File moved out of the active list. Its S3 versions may still exist."})

        if method == "GET" and path.endswith("/versions"):
            file_id = query_params(event).get("fileId")
            item = table.get_item(Key={"fileId": str(file_id or "")}).get("Item")
            if not item:
                return response(404, {"error": "File not found."})
            result = s3.list_object_versions(Bucket=BUCKET, Prefix=item["s3Key"])
            versions = []
            for v in result.get("Versions", []):
                if v.get("Key") == item["s3Key"]:
                    versions.append({
                        "versionId": v["VersionId"],
                        "lastModified": v["LastModified"].isoformat(),
                        "size": v["Size"],
                        "isLatest": v["IsLatest"]
                    })
            versions.sort(key=lambda v: v["lastModified"], reverse=True)
            return response(200, {"versions": versions})

        if method == "POST" and path.endswith("/restore"):
            data = body_json(event)
            file_id = str(data.get("fileId", ""))
            version_id = str(data.get("versionId", ""))
            item = table.get_item(Key={"fileId": file_id}).get("Item")
            if not item or not version_id:
                return response(404, {"error": "File or version not found."})
            # Copy the selected historical version to the same key as a new current version.
            s3.copy_object(
                Bucket=BUCKET,
                Key=item["s3Key"],
                CopySource={"Bucket": BUCKET, "Key": item["s3Key"], "VersionId": version_id}
            )
            table.update_item(
                Key={"fileId": file_id},
                UpdateExpression="SET isDeleted = :f",
                ExpressionAttributeValues={":f": False}
            )
            return response(200, {"message": "Selected version restored as the current version."})

        return response(404, {"error": "Route not found.", "path": path, "method": method})

    except Exception as exc:
        print("Unhandled error:", repr(exc))
        return response(500, {"error": "Internal server error. Check the Lambda CloudWatch logs."})
