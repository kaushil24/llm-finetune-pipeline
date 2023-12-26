import unittest
import os
import tempfile
import shutil
from pathlib import Path
from libs.blob import *


class TestBlobStore(unittest.TestCase):
    """
    Thanks ChatGPT. 
    @todo Write better NON-AI test cases
    """
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.blobstore_local_config = BlobStoreConfig(type=BlobStoreType.LOCAL, base_dir=self.temp_dir)
        self.blobstore_azure_config = BlobStoreConfig(type=BlobStoreType.AZURE, uri="your_azure_blob_uri")

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_write_file_local(self):
        blobstore = BlobStore(self.blobstore_local_config)
        source_file = os.path.join(self.temp_dir, "test_file.txt")
        with open(source_file, "w") as f:
            f.write("Test content")

        destination = ["folder", "subfolder"]
        result = blobstore.write_file(source_file, destination)

        expected_path = os.path.join(self.temp_dir, *destination, "test_file.txt")
        self.assertTrue(os.path.exists(expected_path))
        self.assertEqual(result, expected_path)

    def test_zip_and_write_folder_local(self):
        blobstore = BlobStore(self.blobstore_local_config)
        source_folder = os.path.join(self.temp_dir, "test_folder")
        os.makedirs(source_folder)
        source_file = os.path.join(source_folder, "test_file.txt")
        with open(source_file, "w") as f:
            f.write("Test content")

        destination = ["folder", "subfolder"]
        zip_name = "test_zip"

        result = blobstore.zip_and_write_folder(source_folder, destination, zip_name)

        expected_path = os.path.join(self.temp_dir, *destination, f"{zip_name}.zip")
        self.assertTrue(os.path.exists(expected_path))
        self.assertEqual(result, expected_path)


if __name__ == '__main__':
    unittest.main()
