"""
Sync exported PLUTO assets to a Cloudflare R2 bucket (or any S3-compatible store).

Bucket layout (relative to R2_PREFIX, if set):

    manifest.json                         # what's in the bucket, schemas, row counts
    parquet/core/year=YYYY/data.parquet   # normalized, all-years-compatible columns
    parquet/full/year=YYYY/data.parquet   # every harmonized column for that year
    fgb/plutoYY.fgb                       # FlatGeobuf, EPSG:2263, spatial index
    pmtiles/plutoYY_shp_wgs.pmtiles       # vector tiles used by the frontend
"""

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import boto3
import duckdb
from boto3.s3.transfer import TransferConfig
from botocore.config import Config
from botocore.exceptions import ClientError

from .constants import ASSETS_DIR
from .schema import CORE_COLUMNS, EXPORT_CRS, SOURCE_CRS

MANIFEST_VERSION = 1
SHA256_METADATA_KEY = "sha256"

# local directory under ASSETS_DIR -> (bucket directory, file suffix)
SYNC_DIRS = {
    "parquet": ("parquet", ".parquet"),
    "fgbs": ("fgb", ".fgb"),
    "tilesets": ("pmtiles", ".pmtiles"),
}

CONTENT_TYPES = {
    ".parquet": "application/vnd.apache.parquet",
    ".fgb": "application/octet-stream",
    ".pmtiles": "application/vnd.pmtiles",
    ".json": "application/json",
}


@dataclass
class R2Config:
    bucket: str
    endpoint_url: str
    access_key_id: str
    secret_access_key: str
    prefix: str = ""
    public_base_url: str | None = None

    @classmethod
    def from_env(cls) -> "R2Config":
        """
        Read R2 settings from the environment.

        R2_ENDPOINT_URL takes precedence over R2_ACCOUNT_ID so the same code can
        target LocalStack/MinIO in development.
        """
        endpoint_url = os.environ.get("R2_ENDPOINT_URL")
        account_id = os.environ.get("R2_ACCOUNT_ID")
        if not endpoint_url and account_id:
            endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"

        missing = [
            name
            for name, value in {
                "R2_BUCKET": os.environ.get("R2_BUCKET"),
                "R2_ENDPOINT_URL or R2_ACCOUNT_ID": endpoint_url,
                "R2_ACCESS_KEY_ID": os.environ.get("R2_ACCESS_KEY_ID"),
                "R2_SECRET_ACCESS_KEY": os.environ.get("R2_SECRET_ACCESS_KEY"),
            }.items()
            if not value
        ]
        if missing:
            raise ValueError(f"Missing R2 configuration: {', '.join(missing)}")

        return cls(
            bucket=os.environ["R2_BUCKET"],
            endpoint_url=endpoint_url,  # pyright: ignore
            access_key_id=os.environ["R2_ACCESS_KEY_ID"],
            secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
            prefix=os.environ.get("R2_PREFIX", "").strip("/"),
            public_base_url=os.environ.get("R2_PUBLIC_BASE_URL"),
        )

    def key(self, relative_key: str) -> str:
        return f"{self.prefix}/{relative_key}" if self.prefix else relative_key

    def client(self):
        return boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            region_name="auto",
            config=Config(
                s3={"addressing_style": "path"},
                retries={"max_attempts": 5, "mode": "standard"},
                # R2 rejects the default CRC32 checksums newer boto3 sends
                request_checksum_calculation="when_required",
                response_checksum_validation="when_required",
            ),
        )


def sha256_file(path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def local_assets(assets_dir: str | Path = ASSETS_DIR) -> dict[str, Path]:
    """
    Map bucket-relative keys to local files for every syncable asset.
    """
    assets_dir = Path(assets_dir)
    files: dict[str, Path] = {}

    for local_dir, (bucket_dir, suffix) in SYNC_DIRS.items():
        root = assets_dir / local_dir
        if not root.exists():
            continue
        for path in sorted(root.rglob(f"*{suffix}")):
            files[f"{bucket_dir}/{path.relative_to(root).as_posix()}"] = path

    return files


def _parquet_summary(conn, path: Path) -> dict:
    columns = conn.execute(
        "SELECT column_name, column_type FROM (DESCRIBE SELECT * FROM read_parquet(?))",
        [str(path)],
    ).fetchall()
    (row_count,) = conn.execute(
        "SELECT sum(num_rows) FROM parquet_file_metadata(?)", [str(path)]
    ).fetchone()  # pyright: ignore
    return {
        "row_count": int(row_count or 0),
        "columns": [{"name": name, "type": type_} for name, type_ in columns],
    }


def build_manifest(files: dict[str, Path], config: R2Config | None = None) -> dict:
    """
    Describe what is in the bucket. The parcel data MCP server reads this to
    report available years, file locations, row counts and per-year schemas.
    """
    conn = duckdb.connect()
    conn.execute("INSTALL spatial; LOAD spatial;")

    datasets: dict[str, dict] = {}
    other_files: list[dict] = []

    for key, path in sorted(files.items()):
        entry = {"key": key, "size_bytes": path.stat().st_size}
        parts = key.split("/")

        if parts[0] == "parquet" and len(parts) == 4 and parts[2].startswith("year="):
            dataset = parts[1]
            year = int(parts[2].removeprefix("year="))
            entry |= {"year": year, **_parquet_summary(conn, path)}
            datasets.setdefault(dataset, {"files": []})["files"].append(entry)
        else:
            other_files.append(entry)

    for dataset in datasets.values():
        dataset["years"] = sorted(f["year"] for f in dataset["files"])
        dataset["row_count"] = sum(f["row_count"] for f in dataset["files"])

    return {
        "version": MANIFEST_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "bucket": config.bucket if config else None,
        "prefix": config.prefix if config else "",
        "public_base_url": config.public_base_url if config else None,
        "crs": {"parquet": EXPORT_CRS, "fgb": SOURCE_CRS},
        "core_columns": CORE_COLUMNS,
        "datasets": datasets,
        "files": other_files,
    }


def _remote_sha256(client, bucket: str, key: str) -> str | None:
    try:
        head = client.head_object(Bucket=bucket, Key=key)
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") in ("404", "NoSuchKey", "NotFound"):
            return None
        raise
    return head.get("Metadata", {}).get(SHA256_METADATA_KEY)


def _ensure_bucket(client, bucket: str) -> None:
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError:
        print(f"Creating bucket {bucket}")
        client.create_bucket(Bucket=bucket)


def sync_to_r2(
    dry_run: bool = False,
    force: bool = False,
    create_bucket: bool = False,
    only: tuple[str, ...] = (),
) -> None:
    """
    Upload exported assets and a manifest.json to R2.

    Files whose sha256 matches the object metadata in the bucket are skipped, so
    re-running the sync only uploads what changed.
    """
    config = R2Config.from_env()
    client = config.client()

    files = local_assets()
    if only:
        files = {k: v for k, v in files.items() if k.split("/")[0] in only}
    if not files:
        raise ValueError(
            f"No assets found in {ASSETS_DIR}. Run export-parquet / export-fgbs / "
            "create-tilesets first."
        )

    if create_bucket and not dry_run:
        _ensure_bucket(client, config.bucket)

    transfer_config = TransferConfig(
        multipart_threshold=64 * 1024 * 1024,
        multipart_chunksize=64 * 1024 * 1024,
        max_concurrency=8,
    )

    uploaded, skipped = 0, 0
    for relative_key, path in files.items():
        key = config.key(relative_key)
        local_sha = sha256_file(path)

        if not force and _remote_sha256(client, config.bucket, key) == local_sha:
            skipped += 1
            continue

        size_mb = path.stat().st_size / 1024 / 1024
        print(f"{'[dry-run] ' if dry_run else ''}Uploading {key} ({size_mb:.1f} MB)")
        if dry_run:
            continue

        client.upload_file(
            str(path),
            config.bucket,
            key,
            ExtraArgs={
                "ContentType": CONTENT_TYPES.get(
                    path.suffix, "application/octet-stream"
                ),
                "Metadata": {SHA256_METADATA_KEY: local_sha},
            },
            Config=transfer_config,
        )
        uploaded += 1

    # The manifest always describes everything available locally, not just `only`.
    manifest = build_manifest(local_assets(), config)
    manifest_path = Path(ASSETS_DIR) / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"Wrote {manifest_path}")

    if not dry_run:
        client.put_object(
            Bucket=config.bucket,
            Key=config.key("manifest.json"),
            Body=manifest_path.read_bytes(),
            ContentType=CONTENT_TYPES[".json"],
            CacheControl="max-age=300",
        )

    print(
        f"Done. {uploaded} uploaded, {skipped} unchanged"
        f"{' (dry run, nothing uploaded)' if dry_run else ''}."
    )
