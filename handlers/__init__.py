# Import order matters: broad text handlers should be loaded last.
from . import admin, menu, registration, search, shop, blind_chat  # noqa: F401
