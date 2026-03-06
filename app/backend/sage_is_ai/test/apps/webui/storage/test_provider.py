import io
import os
import boto3
import pytest
from botocore.exceptions import ClientError
from moto import mock_aws
from sage_is_ai.storage import provider
from gcp_storage_emulator.server import create_server
from google.cloud import storage
from azure.storage.blob import (
    BlobServiceClient,
    ContainerClient,
    BlobClient,
)
from unittest.mock import MagicMock
from dataclasses import dataclass
from typing import Any, Dict

# Import azure if available, otherwise create mock
try:
    import azure.storage.blob
except ImportError:
    class MockAzureModule:
        class blob:
            BlobServiceClient = MagicMock
            ContainerClient = MagicMock
            BlobClient = MagicMock
    
    azure = MockAzureModule()


@dataclass
class StorageTestData:
    """Common test data for all storage provider tests"""
    file_content: bytes = b"test content"
    filename: str = "test.txt"
    filename_extra: str = "test_extra.txt"
    
    @property
    def file_bytesio(self):
        return io.BytesIO(self.file_content)
    
    @property
    def file_bytesio_empty(self):
        return io.BytesIO()


class AssertionHelpers:
    """Common assertion patterns for storage provider tests"""
    
    @staticmethod
    def assert_file_uploaded_locally(upload_dir, filename, expected_content):
        """Assert file exists locally with expected content"""
        file_path = upload_dir / filename
        assert file_path.exists()
        assert file_path.read_bytes() == expected_content
    
    @staticmethod
    def assert_file_not_exists_locally(upload_dir, filename):
        """Assert file does not exist locally"""
        file_path = upload_dir / filename
        assert not file_path.exists()
    
    @staticmethod
    def assert_s3_object_exists(s3_client, bucket_name, key, expected_content):
        """Assert S3 object exists with expected content"""
        obj = s3_client.Object(bucket_name, key)
        assert expected_content == obj.get()["Body"].read()
    
    @staticmethod
    def assert_s3_object_deleted(s3_client, bucket_name, key):
        """Assert S3 object is deleted"""
        with pytest.raises(ClientError) as exc:
            s3_client.Object(bucket_name, key).load()
        error = exc.value.response["Error"]
        assert error["Code"] == "404"
        assert error["Message"] == "Not Found"
    
    @staticmethod
    def assert_gcs_blob_exists(bucket, filename, expected_content):
        """Assert GCS blob exists with expected content"""
        blob = bucket.get_blob(filename)
        assert expected_content == blob.download_as_bytes()
    
    @staticmethod
    def assert_gcs_blob_deleted(bucket, filename):
        """Assert GCS blob is deleted"""
        assert bucket.get_blob(filename) is None


class MockFactory:
    """Factory for creating consistent mocks across storage providers"""
    
    @staticmethod
    def create_azure_mocks(monkeypatch):
        """Create Azure-specific mocks"""
        mock_blob_service_client = MagicMock()
        mock_container_client = MagicMock()
        mock_blob_client = MagicMock()
        
        mock_blob_service_client.get_container_client.return_value = mock_container_client
        mock_container_client.get_blob_client.return_value = mock_blob_client
        
        try:
            import azure.storage.blob
            monkeypatch.setattr(
                azure.storage.blob, "BlobServiceClient",
                lambda *args, **kwargs: mock_blob_service_client,
            )
            monkeypatch.setattr(
                azure.storage.blob, "ContainerClient",
                lambda *args, **kwargs: mock_container_client,
            )
            monkeypatch.setattr(
                azure.storage.blob, "BlobClient",
                lambda *args, **kwargs: mock_blob_client,
            )
        except ImportError:
            # If azure is not available, the provider will use mocks
            pass
        
        return {
            'blob_service_client': mock_blob_service_client,
            'container_client': mock_container_client,
            'blob_client': mock_blob_client
        }


@pytest.fixture
def storage_test_data():
    """Fixture providing common test data for all storage provider tests"""
    return StorageTestData()


@pytest.fixture
def mock_upload_directory(monkeypatch, tmp_path):
    """Fixture to monkey-patch the UPLOAD_DIR and create a temporary directory."""
    directory = tmp_path / "uploads"
    directory.mkdir()
    monkeypatch.setattr(provider, "UPLOAD_DIR", str(directory))
    return directory


def mock_upload_dir(monkeypatch, tmp_path):
    """Fixture to monkey-patch the UPLOAD_DIR and create a temporary directory."""
    directory = tmp_path / "uploads"
    directory.mkdir()
    monkeypatch.setattr(provider, "UPLOAD_DIR", str(directory))
    return directory


def test_imports():
    provider.StorageProvider
    provider.LocalStorageProvider
    provider.S3StorageProvider
    provider.GCSStorageProvider
    provider.AzureStorageProvider
    provider.Storage


@pytest.mark.parametrize("provider_type,expected_instance", [
    ("local", provider.LocalStorageProvider),
    ("s3", provider.S3StorageProvider),
    ("gcs", provider.GCSStorageProvider),
    ("azure", provider.AzureStorageProvider),
])
def test_get_storage_provider(provider_type, expected_instance):
    """Test that get_storage_provider returns the correct provider type"""
    Storage = provider.get_storage_provider(provider_type)
    assert isinstance(Storage, expected_instance)


def test_get_storage_provider_invalid():
    """Test that get_storage_provider raises error for invalid provider"""
    with pytest.raises(RuntimeError):
        provider.get_storage_provider("invalid")


@pytest.mark.parametrize("provider_class", [
    provider.LocalStorageProvider,
    provider.S3StorageProvider,
    provider.GCSStorageProvider,
    provider.AzureStorageProvider,
])
def test_class_instantiation(provider_class):
    """Test that all concrete providers can be instantiated"""
    instance = provider_class()
    assert instance is not None


def test_abstract_class_instantiation():
    """Test that abstract base class cannot be instantiated"""
    with pytest.raises(TypeError):
        provider.StorageProvider()
    
    with pytest.raises(TypeError):
        class Test(provider.StorageProvider):
            pass
        Test()


class TestLocalStorageProvider:
    """Test Local Storage Provider with DRY pattern"""
    
    @pytest.fixture
    def storage(self):
        return provider.LocalStorageProvider()

    def test_upload_file(self, storage, storage_test_data, mock_upload_directory):
        contents, file_path = storage.upload_file(
            storage_test_data.file_bytesio, storage_test_data.filename
        )
        
        # Verify local file exists with correct content
        AssertionHelpers.assert_file_uploaded_locally(
            mock_upload_directory, storage_test_data.filename, storage_test_data.file_content
        )
        
        # Verify return values
        assert contents == storage_test_data.file_content
        assert file_path == str(mock_upload_directory / storage_test_data.filename)
        
        # Test empty file error
        with pytest.raises(ValueError):
            storage.upload_file(storage_test_data.file_bytesio_empty, storage_test_data.filename)

    def test_get_file(self, storage, storage_test_data, mock_upload_directory):
        file_path = str(mock_upload_directory / storage_test_data.filename)
        file_path_return = storage.get_file(file_path)
        assert file_path == file_path_return

    def test_delete_file(self, storage, storage_test_data, mock_upload_directory):
        # Create test file
        (mock_upload_directory / storage_test_data.filename).write_bytes(storage_test_data.file_content)
        assert (mock_upload_directory / storage_test_data.filename).exists()
        
        # Delete and verify
        file_path = str(mock_upload_directory / storage_test_data.filename)
        storage.delete_file(file_path)
        AssertionHelpers.assert_file_not_exists_locally(mock_upload_directory, storage_test_data.filename)

    def test_delete_all_files(self, storage, storage_test_data, mock_upload_directory):
        # Create test files
        (mock_upload_directory / storage_test_data.filename).write_bytes(storage_test_data.file_content)
        (mock_upload_directory / storage_test_data.filename_extra).write_bytes(storage_test_data.file_content)
        
        # Delete all and verify
        storage.delete_all_files()
        AssertionHelpers.assert_file_not_exists_locally(mock_upload_directory, storage_test_data.filename)
        AssertionHelpers.assert_file_not_exists_locally(mock_upload_directory, storage_test_data.filename_extra)


@mock_aws
class TestS3StorageProvider:
    """Test S3 Storage Provider with DRY pattern"""

    @pytest.fixture
    def storage(self):
        storage = provider.S3StorageProvider()
        storage.bucket_name = "my-bucket"
        return storage

    @pytest.fixture
    def s3_client(self):
        return boto3.resource("s3", region_name="us-east-1")

    def test_upload_file(self, storage, s3_client, storage_test_data, mock_upload_directory):
        # Test error when bucket doesn't exist
        with pytest.raises(Exception):
            storage.upload_file(
                storage_test_data.file_bytesio, storage_test_data.filename
            )
        
        # Create bucket and test successful upload
        s3_client.create_bucket(Bucket=storage.bucket_name)
        contents, s3_file_path = storage.upload_file(
            storage_test_data.file_bytesio, storage_test_data.filename
        )
        
        # Verify S3 object exists
        AssertionHelpers.assert_s3_object_exists(
            s3_client, storage.bucket_name, storage_test_data.filename, storage_test_data.file_content
        )
        
        # Verify local file exists
        AssertionHelpers.assert_file_uploaded_locally(
            mock_upload_directory, storage_test_data.filename, storage_test_data.file_content
        )
        
        # Verify return values
        assert contents == storage_test_data.file_content
        assert s3_file_path == f"s3://{storage.bucket_name}/{storage_test_data.filename}"
        
        # Test empty file error
        with pytest.raises(ValueError):
            storage.upload_file(storage_test_data.file_bytesio_empty, storage_test_data.filename)

    def test_get_file(self, storage, s3_client, storage_test_data, mock_upload_directory):
        s3_client.create_bucket(Bucket=storage.bucket_name)
        contents, s3_file_path = storage.upload_file(
            storage_test_data.file_bytesio, storage_test_data.filename
        )
        file_path = storage.get_file(s3_file_path)
        assert file_path == str(mock_upload_directory / storage_test_data.filename)
        assert (mock_upload_directory / storage_test_data.filename).exists()

    def test_delete_file(self, storage, s3_client, storage_test_data, mock_upload_directory):
        s3_client.create_bucket(Bucket=storage.bucket_name)
        contents, s3_file_path = storage.upload_file(
            storage_test_data.file_bytesio, storage_test_data.filename
        )
        assert (mock_upload_directory / storage_test_data.filename).exists()
        
        storage.delete_file(s3_file_path)
        
        # Verify local file deleted
        AssertionHelpers.assert_file_not_exists_locally(mock_upload_directory, storage_test_data.filename)
        
        # Verify S3 object deleted
        AssertionHelpers.assert_s3_object_deleted(s3_client, storage.bucket_name, storage_test_data.filename)

    def test_delete_all_files(self, storage, s3_client, storage_test_data, mock_upload_directory):
        s3_client.create_bucket(Bucket=storage.bucket_name)
        
        # Create test files
        storage.upload_file(storage_test_data.file_bytesio, storage_test_data.filename)
        storage.upload_file(io.BytesIO(storage_test_data.file_content), storage_test_data.filename_extra)
        
        # Verify files exist
        AssertionHelpers.assert_s3_object_exists(
            s3_client, storage.bucket_name, storage_test_data.filename, storage_test_data.file_content
        )
        AssertionHelpers.assert_s3_object_exists(
            s3_client, storage.bucket_name, storage_test_data.filename_extra, storage_test_data.file_content
        )
        
        # Delete all files
        storage.delete_all_files()
        
        # Verify files deleted locally
        AssertionHelpers.assert_file_not_exists_locally(mock_upload_directory, storage_test_data.filename)
        AssertionHelpers.assert_file_not_exists_locally(mock_upload_directory, storage_test_data.filename_extra)
        
        # Verify files deleted from S3
        AssertionHelpers.assert_s3_object_deleted(s3_client, storage.bucket_name, storage_test_data.filename)
        AssertionHelpers.assert_s3_object_deleted(s3_client, storage.bucket_name, storage_test_data.filename_extra)

    def test_init_without_credentials(self, monkeypatch):
        """Test that S3StorageProvider can initialize without explicit credentials."""
        # Temporarily unset the environment variables
        monkeypatch.setattr(provider, "S3_ACCESS_KEY_ID", None)
        monkeypatch.setattr(provider, "S3_SECRET_ACCESS_KEY", None)

        # Should not raise an exception
        storage = provider.S3StorageProvider()
        assert storage.s3_client is not None
        assert storage.bucket_name == provider.S3_BUCKET_NAME


class TestGCSStorageProvider:
    """Test GCS Storage Provider with DRY pattern"""
    
    @pytest.fixture
    def storage(self):
        storage = provider.GCSStorageProvider()
        storage.bucket_name = "my-bucket"
        return storage

    @pytest.fixture(scope="class")
    def setup_gcs_emulator(self):
        """Setup GCS emulator with proper initialization"""
        host, port = "localhost", 9023
        server = create_server(host, port, in_memory=True)
        server.start()
        os.environ["STORAGE_EMULATOR_HOST"] = f"http://{host}:{port}"
        
        gcs_client = storage.Client()
        bucket_name = "my-bucket"
        bucket = gcs_client.bucket(bucket_name)
        bucket.create()
        
        yield gcs_client, bucket
        
        bucket.delete(force=True)
        server.stop()

    def test_upload_file(self, storage, storage_test_data, mock_upload_directory, setup_gcs_emulator):
        gcs_client, bucket = setup_gcs_emulator
        storage.gcs_client = gcs_client
        storage.bucket = bucket
        
        # Test bucket error first
        original_bucket = storage.bucket
        storage.bucket = None
        with pytest.raises(Exception):
            storage.upload_file(storage_test_data.file_bytesio, storage_test_data.filename)
        storage.bucket = original_bucket
        
        # Test successful upload
        contents, gcs_file_path = storage.upload_file(
            storage_test_data.file_bytesio, storage_test_data.filename
        )
        
        # Verify GCS blob exists
        AssertionHelpers.assert_gcs_blob_exists(bucket, storage_test_data.filename, storage_test_data.file_content)
        
        # Verify local file exists
        AssertionHelpers.assert_file_uploaded_locally(
            mock_upload_directory, storage_test_data.filename, storage_test_data.file_content
        )
        
        # Verify return values
        assert contents == storage_test_data.file_content
        assert gcs_file_path == f"gs://{storage.bucket_name}/{storage_test_data.filename}"
        
        # Test empty file error
        with pytest.raises(ValueError):
            storage.upload_file(storage_test_data.file_bytesio_empty, storage_test_data.filename)

    def test_get_file(self, storage, storage_test_data, mock_upload_directory, setup_gcs_emulator):
        gcs_client, bucket = setup_gcs_emulator
        storage.gcs_client = gcs_client
        storage.bucket = bucket
        
        contents, gcs_file_path = storage.upload_file(
            storage_test_data.file_bytesio, storage_test_data.filename
        )
        file_path = storage.get_file(gcs_file_path)
        assert file_path == str(mock_upload_directory / storage_test_data.filename)
        assert (mock_upload_directory / storage_test_data.filename).exists()

    def test_delete_file(self, storage, storage_test_data, mock_upload_directory, setup_gcs_emulator):
        gcs_client, bucket = setup_gcs_emulator
        storage.gcs_client = gcs_client
        storage.bucket = bucket
        
        contents, gcs_file_path = storage.upload_file(
            storage_test_data.file_bytesio, storage_test_data.filename
        )
        
        # Ensure local file exists and GCS blob exists
        assert (mock_upload_directory / storage_test_data.filename).exists()
        assert bucket.get_blob(storage_test_data.filename).name == storage_test_data.filename
        
        storage.delete_file(gcs_file_path)
        
        # Verify both local and GCS deletion
        AssertionHelpers.assert_file_not_exists_locally(mock_upload_directory, storage_test_data.filename)
        AssertionHelpers.assert_gcs_blob_deleted(bucket, storage_test_data.filename)

    def test_delete_all_files(self, storage, storage_test_data, mock_upload_directory, setup_gcs_emulator):
        gcs_client, bucket = setup_gcs_emulator
        storage.gcs_client = gcs_client
        storage.bucket = bucket
        
        # Create test files
        storage.upload_file(storage_test_data.file_bytesio, storage_test_data.filename)
        storage.upload_file(io.BytesIO(storage_test_data.file_content), storage_test_data.filename_extra)
        
        # Verify files exist locally and in GCS
        AssertionHelpers.assert_file_uploaded_locally(
            mock_upload_directory, storage_test_data.filename, storage_test_data.file_content
        )
        AssertionHelpers.assert_file_uploaded_locally(
            mock_upload_directory, storage_test_data.filename_extra, storage_test_data.file_content
        )
        AssertionHelpers.assert_gcs_blob_exists(bucket, storage_test_data.filename, storage_test_data.file_content)
        AssertionHelpers.assert_gcs_blob_exists(bucket, storage_test_data.filename_extra, storage_test_data.file_content)
        
        # Delete all files
        storage.delete_all_files()
        
        # Verify all files deleted
        AssertionHelpers.assert_file_not_exists_locally(mock_upload_directory, storage_test_data.filename)
        AssertionHelpers.assert_file_not_exists_locally(mock_upload_directory, storage_test_data.filename_extra)
        AssertionHelpers.assert_gcs_blob_deleted(bucket, storage_test_data.filename)
        AssertionHelpers.assert_gcs_blob_deleted(bucket, storage_test_data.filename_extra)


class TestAzureStorageProvider:
    """Test Azure Storage Provider with DRY pattern using MockFactory"""
    
    @pytest.fixture
    def storage(self):
        return provider.AzureStorageProvider()

    @pytest.fixture
    def setup_azure_mocks(self, monkeypatch):
        """Setup Azure mocks using MockFactory"""
        mocks = MockFactory.create_azure_mocks(monkeypatch)
        
        storage = provider.AzureStorageProvider()
        storage.endpoint = "https://myaccount.blob.core.windows.net"
        storage.container_name = "my-container"
        
        # Apply mocks to the storage instance
        storage.blob_service_client = mocks['blob_service_client']
        storage.container_client = mocks['container_client']
        
        return storage, mocks

    def test_upload_file(self, storage_test_data, mock_upload_directory, setup_azure_mocks):
        storage, mocks = setup_azure_mocks
        
        # Simulate error when container doesn't exist
        mocks['container_client'].get_blob_client.side_effect = Exception("Container does not exist")
        with pytest.raises(Exception):
            storage.upload_file(storage_test_data.file_bytesio, storage_test_data.filename)
        
        # Reset side effect and create container
        mocks['container_client'].get_blob_client.side_effect = None
        storage.create_container()
        contents, azure_file_path = storage.upload_file(
            storage_test_data.file_bytesio, storage_test_data.filename
        )
        
        # Verify mocks were called correctly
        mocks['container_client'].get_blob_client.assert_called_with(storage_test_data.filename)
        mocks['blob_client'].upload_blob.assert_called_once_with(
            storage_test_data.file_content, overwrite=True
        )
        
        # Verify return values and local file
        assert contents == storage_test_data.file_content
        assert azure_file_path == f"{storage.endpoint}/{storage.container_name}/{storage_test_data.filename}"
        AssertionHelpers.assert_file_uploaded_locally(
            mock_upload_directory, storage_test_data.filename, storage_test_data.file_content
        )
        
        # Test empty file error
        with pytest.raises(ValueError):
            storage.upload_file(storage_test_data.file_bytesio_empty, storage_test_data.filename)

    def test_get_file(self, storage_test_data, mock_upload_directory, setup_azure_mocks):
        storage, mocks = setup_azure_mocks
        storage.create_container()
        
        # Mock upload behavior
        storage.upload_file(storage_test_data.file_bytesio, storage_test_data.filename)
        
        # Mock blob download behavior
        mocks['blob_client'].download_blob().readall.return_value = storage_test_data.file_content
        
        file_url = f"{storage.endpoint}/{storage.container_name}/{storage_test_data.filename}"
        file_path = storage.get_file(file_url)
        
        assert file_path == str(mock_upload_directory / storage_test_data.filename)
        AssertionHelpers.assert_file_uploaded_locally(
            mock_upload_directory, storage_test_data.filename, storage_test_data.file_content
        )

    def test_delete_file(self, storage_test_data, mock_upload_directory, setup_azure_mocks):
        storage, mocks = setup_azure_mocks
        storage.create_container()
        
        # Mock file upload
        storage.upload_file(storage_test_data.file_bytesio, storage_test_data.filename)
        
        # Mock deletion
        mocks['blob_client'].delete_blob.return_value = None
        
        file_url = f"{storage.endpoint}/{storage.container_name}/{storage_test_data.filename}"
        storage.delete_file(file_url)
        
        mocks['blob_client'].delete_blob.assert_called_once()
        AssertionHelpers.assert_file_not_exists_locally(mock_upload_directory, storage_test_data.filename)

    def test_delete_all_files(self, storage_test_data, mock_upload_directory, setup_azure_mocks):
        storage, mocks = setup_azure_mocks
        storage.create_container()
        
        # Mock file uploads
        storage.upload_file(storage_test_data.file_bytesio, storage_test_data.filename)
        storage.upload_file(io.BytesIO(storage_test_data.file_content), storage_test_data.filename_extra)
        
        # Mock listing and deletion behavior
        mocks['container_client'].list_blobs.return_value = [
            {"name": storage_test_data.filename},
            {"name": storage_test_data.filename_extra},
        ]
        mocks['blob_client'].delete_blob.return_value = None
        
        storage.delete_all_files()
        
        mocks['container_client'].list_blobs.assert_called_once()
        mocks['blob_client'].delete_blob.assert_any_call()
        AssertionHelpers.assert_file_not_exists_locally(mock_upload_directory, storage_test_data.filename)
        AssertionHelpers.assert_file_not_exists_locally(mock_upload_directory, storage_test_data.filename_extra)

    def test_get_file_not_found(self, storage_test_data, setup_azure_mocks):
        storage, mocks = setup_azure_mocks
        storage.create_container()
        
        file_url = f"{storage.endpoint}/{storage.container_name}/{storage_test_data.filename}"
        # Mock behavior to raise an error for missing blobs
        mocks['blob_client'].download_blob.side_effect = Exception("Blob not found")
        
        with pytest.raises(Exception, match="Blob not found"):
            storage.get_file(file_url)
