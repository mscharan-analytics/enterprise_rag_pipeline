import os
import shutil
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from src.config import S3_BUCKET_NAME, S3_PREFIX
from src.utils.logger import setup_logger

logger = setup_logger("s3_connection")

class S3ConnectionManager:
    """
    Manages connections and downloads from AWS S3 Buckets / Data Lakehouses.
    Falls back to a local simulated S3 directory if credentials are not configured.
    """
    def __init__(self, bucket_name: str = S3_BUCKET_NAME, prefix: str = S3_PREFIX):
        self.bucket_name = bucket_name
        self.prefix = prefix
        self._s3 = None
        self._is_mock = False
        
        # Local mock bucket folder path
        self.mock_dir = "./data/s3_lakehouse"

    def connect(self) -> bool:
        """
        Attempts to establish a live connection with AWS S3. 
        Returns True if connected to AWS, False if operating in Mock/local fallback mode.
        """
        if self._s3 is not None:
            return True
        if self._is_mock:
            return False
            
        try:
            # Initialize client (will load from environment keys if present)
            session = boto3.Session()
            s3 = session.client("s3")
            
            # Make a light call to confirm credentials work
            s3.list_objects_v2(Bucket=self.bucket_name, MaxKeys=1)
            self._s3 = s3
            logger.info(f"Successfully authenticated with AWS. Connected to S3 bucket '{self.bucket_name}'.")
            return True
        except Exception as e:
            logger.warning(
                f"AWS authentication failed or credentials missing (Details: {e}). "
                f"Switching to local simulated S3 Lakehouse directory: '{self.mock_dir}'"
            )
            self._is_mock = True
            os.makedirs(self.mock_dir, exist_ok=True)
            return False

    def sync_to_local(self, local_dest_dir: str) -> list:
        """
        Downloads all objects under prefix from S3 into a local target directory.
        In mock mode, copies files from mock_dir to local_dest_dir.
        Returns a list of downloaded/copied file paths.
        """
        os.makedirs(local_dest_dir, exist_ok=True)
        downloaded_files = []
        
        use_aws = self.connect()
        
        if use_aws:
            try:
                logger.info(f"Syncing files from S3 bucket '{self.bucket_name}' (prefix: '{self.prefix}')...")
                response = self._s3.list_objects_v2(Bucket=self.bucket_name, Prefix=self.prefix)
                
                if "Contents" not in response:
                    logger.info("S3 bucket prefix is empty. No files downloaded.")
                    return []
                    
                for obj in response["Contents"]:
                    s3_key = obj["Key"]
                    if s3_key.endswith("/"):  # Skip directories
                        continue
                        
                    filename = os.path.basename(s3_key)
                    dest_path = os.path.join(local_dest_dir, filename)
                    
                    logger.info(f"Downloading s3://{self.bucket_name}/{s3_key} -> {dest_path}")
                    self._s3.download_file(self.bucket_name, s3_key, dest_path)
                    downloaded_files.append(dest_path)
                    
                return downloaded_files
            except Exception as e:
                logger.error(f"S3 sync operation failed: {e}. Falling back to mock folder.")
                # Force local mock sync on failure
                self._is_mock = True
                
        # Mock connection sync
        logger.info(f"Copying files from local simulated S3 Lakehouse: '{self.mock_dir}' -> '{local_dest_dir}'")
        if not os.path.exists(self.mock_dir) or not os.listdir(self.mock_dir):
            # Seed mock bucket with a default document to prevent empty runs
            os.makedirs(self.mock_dir, exist_ok=True)
            default_file = os.path.join(self.mock_dir, "lakehouse_policy_doc.txt")
            with open(default_file, "w") as f:
                f.write(
                    "STANDARD OPERATING PROCEDURE: SOP-9999\n"
                    "Section: Corporate Governance & Cloud Infrastructure\n"
                    "Subject: Data Lakehouse S3 Retention Guidelines\n"
                    "Effective Date: 2026-07-01\n"
                    "Purpose: To outline standards for storing and synchronizing distributed enterprise documents "
                    "across AWS S3 object store containers and delta lake engines.\n"
                    "Policy: All ingestion pipelines must clean, hash, and format raw files into paragraphs "
                    "using distributed Spark nodes before loading points to vector schemas."
                )
            logger.info(f"Seeded mock lakehouse with default file: {default_file}")
            
        for item in os.listdir(self.mock_dir):
            src_path = os.path.join(self.mock_dir, item)
            if os.path.isfile(src_path) and (item.endswith(".txt") or item.endswith(".pdf")):
                dest_path = os.path.join(local_dest_dir, item)
                shutil.copy2(src_path, dest_path)
                downloaded_files.append(dest_path)
                
        logger.info(f"Copied {len(downloaded_files)} files from simulated S3 folder.")
        return downloaded_files
