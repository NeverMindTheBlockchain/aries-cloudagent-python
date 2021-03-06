from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock
import pytest

from aiohttp.web import HTTPBadRequest, HTTPForbidden, HTTPNotFound

from ...config.injection_context import InjectionContext
from ...storage.base import BaseStorage
from ...storage.basic import BasicStorage

from .. import routes as test_module


class TestRevocationRoutes(AsyncTestCase):
    def setUp(self):
        self.context = InjectionContext(enforce_typing=False)
        self.storage = BasicStorage()
        self.context.injector.bind_instance(BaseStorage, self.storage)
        self.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": self.context,
        }
        self.test_did = "sample-did"

    async def test_create_registry(self):
        CRED_DEF_ID = f"{self.test_did}:3:CL:1234:default"
        request = async_mock.MagicMock()
        request.app = self.app
        request.json = async_mock.CoroutineMock(
            return_value={
                "max_cred_num": "1000",
                "credential_definition_id": CRED_DEF_ID
            }
        )

        with async_mock.patch.object(
            self.storage, "search_records", autospec=True
        ) as mock_search, async_mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as mock_indy_revoc,  async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as mock_json_response:
            mock_search.return_value.fetch_all = async_mock.CoroutineMock(
                return_value=True
            )
            mock_indy_revoc.return_value = async_mock.MagicMock(
                init_issuer_registry=async_mock.CoroutineMock(
                    return_value=async_mock.MagicMock(
                        generate_registry=async_mock.CoroutineMock(),
                        serialize=async_mock.MagicMock(return_value="dummy")
                    )
                )
            )

            result = await test_module.revocation_create_registry(request)
            mock_json_response.assert_called_once_with(
                {"result": "dummy"}
            )
            assert result is mock_json_response.return_value

    async def test_create_registry_no_such_cred_def(self):
        CRED_DEF_ID = f"{self.test_did}:3:CL:1234:default"
        request = async_mock.MagicMock()
        request.app = self.app
        request.json = async_mock.CoroutineMock(
            return_value={
                "max_cred_num": "1000",
                "credential_definition_id": CRED_DEF_ID
            }
        )

        with async_mock.patch.object(
            self.storage, "search_records", autospec=True
        ) as mock_search, async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as mock_json_response:
            mock_search.return_value.fetch_all = async_mock.CoroutineMock(
                return_value=False
            )

            with self.assertRaises(HTTPNotFound):
                result = await test_module.revocation_create_registry(request)
            mock_json_response.assert_not_called()

    async def test_create_registry_no_revo_support(self):
        CRED_DEF_ID = f"{self.test_did}:3:CL:1234:default"
        request = async_mock.MagicMock()
        request.app = self.app
        request.json = async_mock.CoroutineMock(
            return_value={
                "max_cred_num": "1000",
                "credential_definition_id": CRED_DEF_ID
            }
        )

        with async_mock.patch.object(
            self.storage, "search_records", autospec=True
        ) as mock_search, async_mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as mock_indy_revoc,  async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as mock_json_response:
            mock_search.return_value.fetch_all = async_mock.CoroutineMock(
                return_value=True
            )
            mock_indy_revoc.return_value = async_mock.MagicMock(
                init_issuer_registry=async_mock.CoroutineMock(
                    side_effect=test_module.RevocationNotSupportedError(
                        error_code="dummy"
                    )
                )
            )

            with self.assertRaises(HTTPBadRequest):
                result = await test_module.revocation_create_registry(request)

            mock_json_response.assert_not_called()

    async def test_get_current_registry(self):
        REV_REG_ID = "{}:4:{}:3:CL:1234:default:CL_ACCUM:default".format(
            self.test_did,
            self.test_did
        )
        request = async_mock.MagicMock()
        request.app = self.app
        request.match_info = {"id": REV_REG_ID}

        with async_mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as mock_indy_revoc,  async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as mock_json_response:
            mock_indy_revoc.return_value = async_mock.MagicMock(
                get_issuer_revocation_record=async_mock.CoroutineMock(
                    return_value=async_mock.MagicMock(
                        serialize=async_mock.MagicMock(return_value="dummy")
                    )
                )
            )

            result = await test_module.get_current_registry(request)
            mock_json_response.assert_called_once_with(
                {"result": "dummy"}
            )
            assert result is mock_json_response.return_value

    async def test_get_current_registry_not_found(self):
        REV_REG_ID = "{}:4:{}:3:CL:1234:default:CL_ACCUM:default".format(
            self.test_did,
            self.test_did
        )
        request = async_mock.MagicMock()
        request.app = self.app
        request.match_info = {"id": REV_REG_ID}

        with async_mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as mock_indy_revoc,  async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as mock_json_response:
            mock_indy_revoc.return_value = async_mock.MagicMock(
                get_issuer_revocation_record=async_mock.CoroutineMock(
                    side_effect=test_module.StorageNotFoundError(
                        error_code="dummy"
                    )
                )
            )

            with self.assertRaises(HTTPNotFound):
                result = await test_module.get_current_registry(request)
            mock_json_response.assert_not_called()

    async def test_get_tails_file(self):
        REV_REG_ID = "{}:4:{}:3:CL:1234:default:CL_ACCUM:default".format(
            self.test_did,
            self.test_did
        )
        request = async_mock.MagicMock()
        request.app = self.app
        request.match_info = {"id": REV_REG_ID}

        with async_mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as mock_indy_revoc,  async_mock.patch.object(
            test_module.web, "FileResponse", async_mock.Mock()
        ) as mock_file_response:
            mock_indy_revoc.return_value = async_mock.MagicMock(
                get_issuer_revocation_record=async_mock.CoroutineMock(
                    return_value=async_mock.MagicMock(
                        tails_local_path="dummy"
                    )
                )
            )

            result = await test_module.get_tails_file(request)
            mock_file_response.assert_called_once_with(
                path="dummy",
                status=200
            )
            assert result is mock_file_response.return_value

    async def test_get_tails_file_not_found(self):
        REV_REG_ID = "{}:4:{}:3:CL:1234:default:CL_ACCUM:default".format(
            self.test_did,
            self.test_did
        )
        request = async_mock.MagicMock()
        request.app = self.app
        request.match_info = {"id": REV_REG_ID}

        with async_mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as mock_indy_revoc,  async_mock.patch.object(
            test_module.web, "FileResponse", async_mock.Mock()
        ) as mock_file_response:
            mock_indy_revoc.return_value = async_mock.MagicMock(
                get_issuer_revocation_record=async_mock.CoroutineMock(
                    side_effect=test_module.StorageNotFoundError(
                        error_code="dummy"
                    )
                )
            )

            with self.assertRaises(HTTPNotFound):
                result = await test_module.get_tails_file(request)
            mock_file_response.assert_not_called()

    async def test_publish_registry(self):
        REV_REG_ID = "{}:4:{}:3:CL:1234:default:CL_ACCUM:default".format(
            self.test_did,
            self.test_did
        )
        request = async_mock.MagicMock()
        request.app = self.app
        request.match_info = {"id": REV_REG_ID}

        with async_mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as mock_indy_revoc,  async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as mock_json_response:
            mock_indy_revoc.return_value = async_mock.MagicMock(
                get_issuer_revocation_record=async_mock.CoroutineMock(
                    return_value=async_mock.MagicMock(
                        publish_registry_definition=async_mock.CoroutineMock(),
                        publish_registry_entry=async_mock.CoroutineMock(),
                        serialize=async_mock.MagicMock(return_value="dummy")
                    )
                )
            )

            result = await test_module.publish_registry(request)
            mock_json_response.assert_called_once_with(
                {"result": "dummy"}
            )
            assert result is mock_json_response.return_value

    async def test_publish_registry_not_found(self):
        REV_REG_ID = "{}:4:{}:3:CL:1234:default:CL_ACCUM:default".format(
            self.test_did,
            self.test_did
        )
        request = async_mock.MagicMock()
        request.app = self.app
        request.match_info = {"id": REV_REG_ID}

        with async_mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as mock_indy_revoc,  async_mock.patch.object(
            test_module.web, "FileResponse", async_mock.Mock()
        ) as mock_json_response:
            mock_indy_revoc.return_value = async_mock.MagicMock(
                get_issuer_revocation_record=async_mock.CoroutineMock(
                    side_effect=test_module.StorageNotFoundError(
                        error_code="dummy"
                    )
                )
            )

            with self.assertRaises(HTTPNotFound):
                result = await test_module.publish_registry(request)
            mock_json_response.assert_not_called()

    async def test_update_registry(self):
        REV_REG_ID = "{}:4:{}:3:CL:1234:default:CL_ACCUM:default".format(
            self.test_did,
            self.test_did
        )
        request = async_mock.MagicMock()
        request.app = self.app
        request.match_info = {"id": REV_REG_ID}
        request.json = async_mock.CoroutineMock(
            return_value={
                "tails_public_uri": f"http://sample.ca:8181/tails/{REV_REG_ID}"
            }
        )

        with async_mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as mock_indy_revoc,  async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as mock_json_response:
            mock_indy_revoc.return_value = async_mock.MagicMock(
                get_issuer_revocation_record=async_mock.CoroutineMock(
                    return_value=async_mock.MagicMock(
                        set_tails_file_public_uri=async_mock.MagicMock(),
                        save=async_mock.CoroutineMock(),
                        serialize=async_mock.MagicMock(return_value="dummy")
                    )
                )
            )

            result = await test_module.update_registry(request)
            mock_json_response.assert_called_once_with(
                {"result": "dummy"}
            )
            assert result is mock_json_response.return_value

    async def test_update_registry_not_found(self):
        REV_REG_ID = "{}:4:{}:3:CL:1234:default:CL_ACCUM:default".format(
            self.test_did,
            self.test_did
        )
        request = async_mock.MagicMock()
        request.app = self.app
        request.match_info = {"id": REV_REG_ID}
        request.json = async_mock.CoroutineMock(
            return_value={
                "tails_public_uri": f"http://sample.ca:8181/tails/{REV_REG_ID}"
            }
        )

        with async_mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as mock_indy_revoc,  async_mock.patch.object(
            test_module.web, "FileResponse", async_mock.Mock()
        ) as mock_json_response:
            mock_indy_revoc.return_value = async_mock.MagicMock(
                get_issuer_revocation_record=async_mock.CoroutineMock(
                    side_effect=test_module.StorageNotFoundError(
                        error_code="dummy"
                    )
                )
            )

            with self.assertRaises(HTTPNotFound):
                result = await test_module.update_registry(request)
            mock_json_response.assert_not_called()

    async def test_register(self):
        mock_app = async_mock.MagicMock()
        mock_app.add_routes = async_mock.MagicMock()

        await test_module.register(mock_app)
        mock_app.add_routes.assert_called_once()
