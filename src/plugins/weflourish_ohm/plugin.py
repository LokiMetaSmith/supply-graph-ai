from fastapi import FastAPI
from src.plugins.base import BasePlugin, PluginCapability
from .routes import router
from .service import WeFlourishRFQService
from .config import PluginSettings

class Plugin(BasePlugin):
    @property
    def name(self) -> str:
        return "weflourish_ohm"

    @property
    def plugin_api_version(self) -> str:
        return "0.1.0"

    @property
    def capabilities(self) -> list[PluginCapability]:
        return [PluginCapability.NETWORK_EGRESS]

    def initialize(self) -> None:
        """Initialize the WeFlourish RFQ service with plugin settings."""
        # Check if there's a custom settings class
        plugin_settings = self.settings
        if plugin_settings is None:
            plugin_settings = PluginSettings()

        WeFlourishRFQService.get_instance(settings=plugin_settings)

    def register_routes(self, app: FastAPI) -> None:
        """Mount the plugin routes."""
        app.include_router(router)

    async def on_startup(self) -> None:
        """Lifecycle hook: handle any async startup tasks."""
        pass

    async def on_shutdown(self) -> None:
        """Lifecycle hook: handle any async cleanup tasks."""
        pass
