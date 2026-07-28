from runtime.tools.manifest_provider import ManifestProvider

class ManifestLoader:
    """Shim de compatibilité ascendante liant l'ancien ManifestLoader au nouveau ManifestProvider."""
    _provider = None

    @classmethod
    def get_tools(cls):
        if cls._provider is None:
            cls._provider = ManifestProvider()
        return cls._provider.get_tools()