from unittest.mock import patch, MagicMock

_azure_patcher = patch("app.core.azure.client.AzureClient", return_value=MagicMock())
_azure_patcher.start()
