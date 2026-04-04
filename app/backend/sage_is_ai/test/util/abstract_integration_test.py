import logging

from fastapi.testclient import TestClient


log = logging.getLogger(__name__)


def get_fast_api_client():
    from main import app

    with TestClient(app) as c:
        return c


class AbstractIntegrationTest:
    BASE_PATH = None

    def create_url(self, path="", query_params=None):
        if self.BASE_PATH is None:
            raise Exception("BASE_PATH is not set")
        parts = self.BASE_PATH.split("/")
        parts = [part.strip() for part in parts if part.strip() != ""]
        path_parts = path.split("/")
        path_parts = [part.strip() for part in path_parts if part.strip() != ""]
        query_parts = ""
        if query_params:
            query_parts = "&".join(
                [f"{key}={value}" for key, value in query_params.items()]
            )
            query_parts = f"?{query_parts}"
        return "/".join(parts + path_parts) + query_parts

    @classmethod
    def setup_class(cls):
        pass

    def setup_method(self):
        pass

    @classmethod
    def teardown_class(cls):
        pass

    def teardown_method(self):
        pass


