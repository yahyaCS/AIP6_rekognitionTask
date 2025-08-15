import argparse
import csv
import json
import mimetypes
import os
import sys
from typing import Dict, List, Tuple

import boto3
from botocore.exceptions import ClientError, NoCredentialsError, ProfileNotFound


def ensure_bucket_exists(s3_client, bucket: str, region: str) -> None:
    try:
        s3_client.head_bucket(Bucket=bucket)
        return
    except ClientError as e:
        code = e.response.get('Error', {}).get('Code', '')
        http = int(e.response.get('ResponseMetadata', {}).get('HTTPStatusCode', 0))
        if code in {'404', 'NoSuchBucket'} or http == 404:
            params = {'Bucket': bucket}
            if region != 'us-east-1':
                params['CreateBucketConfiguration'] = {'LocationConstraint': region}
            print(f"Creating bucket '{bucket}' in {region}...")
            s3_client.create_bucket(**params)
        else:
            raise


def upload_images(s3_client, bucket: str, images: List[str], prefix: str) -> List[Tuple[str, str]]:
    uploaded: List[Tuple[str, str]] = []
    for local in images:
        if not os.path.isfile(local):
            print(f"[WARN] Skipping missing file: {local}", file=sys.stderr)
            continue
        fname = os.path.basename(local)
        key = f"{prefix.rstrip('/')}/{fname}" if prefix else fname
        ctype, _ = mimetypes.guess_type(local)
        extra = {'ContentType': ctype} if ctype else None
        print(f"Uploading {local} -> s3://{bucket}/{key} ...")
        s3_client.upload_file(local, bucket, key, ExtraArgs=extra or {})
        head = s3_client.head_object(Bucket=bucket, Key=key)
        etag = head.get('ETag', '')
        uploaded.append((key, etag))
    return uploaded


def detect_labels_for_keys(rek_client, bucket: str, keys: List[str], max_labels: int, min_conf: float):
    for key in keys:
        print(f"Detecting labels for s3://{bucket}/{key} ...")
        resp = rek_client.detect_labels(
            Image={'S3Object': {'Bucket': bucket, 'Name': key}},
            MaxLabels=max_labels,
            MinConfidence=min_conf
        )
        labels = [
            {'name': lbl['Name'], 'confidence': float(lbl['Confidence'])}
            for lbl in resp.get('Labels', [])
        ]
        yield key, labels


def write_csv(rows: List[Tuple[str, str, float]], out_csv: str):
    os.makedirs(os.path.dirname(out_csv) or '.', exist_ok=True)
    with open(out_csv, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['s3_key', 'label', 'confidence'])
        for r in rows:
            w.writerow(r)
    print(f"Saved CSV: {out_csv}")


def write_combined_json(results: Dict[str, List[Dict[str, float]]], out_json: str):
    os.makedirs(os.path.dirname(out_json) or '.', exist_ok=True)
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Saved JSON: {out_json}")


def write_per_image_json(results: Dict[str, List[Dict[str, float]]], out_dir: str):
    os.makedirs(out_dir, exist_ok=True)
    for key, labels in results.items():
        fname = key.replace('/', '__')
        path = os.path.join(out_dir, f"{fname}.json")
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({'s3_key': key, 'labels': labels}, f, ensure_ascii=False, indent=2)
    print(f"Saved per-image JSON files in: {out_dir}")


def main():
    p = argparse.ArgumentParser(description="Upload images to S3 and run Rekognition DetectLabels.")
    p.add_argument('--bucket', required=True, help='S3 bucket name (must be globally unique).')
    p.add_argument('--region', default=os.environ.get('AWS_REGION', 'us-east-1'), help='AWS region.')
    p.add_argument('--images', nargs='+', required=True, help='Paths to local images (JPEG/PNG).')
    p.add_argument('--prefix', default='uploads', help='S3 key prefix/folder for uploads.')
    p.add_argument('--out-csv', default='labels.csv', help='CSV output path.')
    p.add_argument('--out-json', default='labels.json', help='Combined JSON output path.')
    p.add_argument('--json-per-image-dir', default=None, help='Write one JSON file per image.')
    p.add_argument('--max-labels', type=int, default=25, help='Max labels per image.')
    p.add_argument('--min-confidence', type=float, default=70.0, help='Min confidence (0-100).')
    p.add_argument('--profile', default=None, help='AWS profile name.')
    args = p.parse_args()

    try:
        session_kwargs = {}
        if args.profile:
            session_kwargs['profile_name'] = args.profile
        session = boto3.Session(**session_kwargs) if session_kwargs else boto3.Session()
        s3_client = session.client('s3', region_name=args.region)
        rek_client = session.client('rekognition', region_name=args.region)
    except ProfileNotFound as e:
        print(f"AWS profile not found: {e}", file=sys.stderr)
        sys.exit(2)

    try:
        ensure_bucket_exists(s3_client, args.bucket, args.region)
    except ClientError as e:
        print(f"Failed to ensure bucket exists: {e}", file=sys.stderr)
        sys.exit(3)

    uploads = upload_images(s3_client, args.bucket, args.images, args.prefix)
    keys = [k for (k, _) in uploads]
    if not keys:
        print("No images uploaded; exiting.", file=sys.stderr)
        sys.exit(4)

    combined: Dict[str, List[Dict[str, float]]] = {}
    csv_rows: List[Tuple[str, str, float]] = []
    try:
        for key, labels in detect_labels_for_keys(rek_client, args.bucket, keys, args.max_labels, args.min_confidence):
            combined[key] = labels
            for item in labels:
                csv_rows.append((key, item['name'], item['confidence']))
    except NoCredentialsError:
        print("No AWS credentials found. Run 'aws configure'.", file=sys.stderr)
        sys.exit(5)
    except ClientError as e:
        print(f"DetectLabels failed: {e}", file=sys.stderr)
        sys.exit(6)

    write_csv(csv_rows, args.out_csv)
    write_combined_json(combined, args.out_json)
    if args.json_per_image_dir:
        write_per_image_json(combined, args.json_per_image_dir)


if __name__ == '__main__':
    main()
