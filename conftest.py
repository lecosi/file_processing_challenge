from unittest.mock import patch, MagicMock

# Patch the already-instantiated module-level object in routers,
# not the class itself — the class is called at import time before
# any class-level patch could take effect.
_azure_patcher = patch("app.api.routers.azure_client", new_callable=MagicMock)
_azure_patcher.start()
