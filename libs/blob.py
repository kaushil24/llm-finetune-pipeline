import os
from dataclasses import dataclass
from enum import Enum
from typing import *
import shutil
from pathlib import Path
import zipfile
import tempfile
from azure.storage.blob import BlobServiceClient
import logging

class BlobStoreType(Enum):
    LOCAL = 'local'
    AZURE = 'azure'

logger = logging.getLogger(__name__)

# @todo: Doesn't make sense to have uri and base_dir.
# Change this to support to have only since param for this.
# Having 2 params, causes an extra step (see model_trainer_pipeline::_get_blob_store_client)
@dataclass
class BlobStoreConfig:
    type: BlobStoreType
    container_name: Optional[str] = None # !! required if using cloud blob !!
    connection_str: Optional[str] = None # !! required if using cloud blob !!
    base_dir: Optional[str] = None

class LocalBlob:
    def __init__(self, base_dir: str) -> None:
        self.base_dir= base_dir

    def write_file(self, source: str, destination: List[str]) -> str:
        full_destination = os.path.join(self.base_dir, '/'.join(destination))
        if not os.path.exists(full_destination):
            os.makedirs(full_destination, exist_ok=True)

        shutil.copy(source, full_destination)
        return os.path.join(full_destination, Path(source).name)

class AzureBlob:
    def __init__(self, connection_string: str, container_name: str) -> None:
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        self.container_client = blob_service_client.get_container_client(container_name)
    
    def write_file(self, source: str, destination: List[str]) -> str:
        file_name = Path(source).name
        blob_name = "/".join(destination + [file_name])
        blob_client = self.container_client.get_blob_client(blob_name)
        with open(source, "rb") as data:
            blob_client.upload_blob(data, overwrite=True)
        return blob_name
    
    def get_file(self, file_path: str, destination_dir: str) -> str:
        # Extract the directory path from the destination path
        blob_client = self.container_client.get_blob_client(file_path)

        # Create the directory if it doesn't exist
        if not os.path.exists(destination_dir):
            os.makedirs(destination_dir)

        # Extract the file name from the blob path
        file_name = Path(file_path).name

        # Combine the destination directory with the file name
        destination_path = os.path.join(destination_dir, file_name)

        # Download the blob content
        with open(destination_path, "wb") as file:
            data = blob_client.download_blob()
            file.write(data.readall())
        return destination_path

class BlobStore:
    def __init__(self, config: Optional[BlobStoreConfig] = None) -> None:
        self.config = config
        print(f"Initializing blobstore client. Type:{config.type}")
        if self.config.type == BlobStoreType.LOCAL:
            self.store = LocalBlob(self.config.base_dir)
        elif self.config.type == BlobStoreType.AZURE:
            self.store = AzureBlob(self.config.connection_str, self.config.container_name)
        else:
            NotImplementedError("Bruhh....")

    def write_file(self, source: str, destination: List[str]) -> str:
        """
        Writes a file from `source` in `destination` (folder in case of local storage and with a prefix in case of cloud blob storage)
        """
        print(f'Beginning to upload {source} at {destination}')
        # @todo: For some weird reason I thought i"d be a good idea to have destination as a list (["parent_dir", "child_Dir"])
        # instead of just having "parent_dir/child_dir/file.txt". Change it everywhere to use normal string only
        return self.store.write_file(source, destination)

    def zip_and_write_folder(self, source: str, destination: List[str], zip_name: str) -> str:
        """
        Zip a folder and write to blob store
        """
        with tempfile.TemporaryDirectory() as tdr:
            zip_file = shutil.make_archive(os.path.join(tdr,zip_name), 'zip', source)
            return self.write_file(zip_file, destination) # @todo: Change this return to something else to accomodate cloud blob stuff

    def get_file(self, file_path: str, desination_dir: str) -> str:
        """
        Gets the file at `file_path` from blob and save it in the `destination` dir.
        Returns where the file is saved locally
        """
        print(f'Beginning to download {file_path} at {desination_dir}')
        if self.config.type == BlobStoreType.LOCAL:
            return self.store.write_file(os.path.join(self.store.base_dir, file_path), desination_dir.split("/"))
        elif self.config.type == BlobStoreType.AZURE:
            return self.store.get_file(file_path, desination_dir)
