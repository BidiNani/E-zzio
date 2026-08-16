import pytest
import asyncio
import os
from core.config.config_provider import ConfigProvider

@pytest.mark.asyncio
async def test_config_provider():
    db_path = "runtime/config/test_config.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    
    config = ConfigProvider(db_path)
    await config.init()
    
    await config.set_config("test_key", "test_value")
    value = await config.get_config("test_key")
    assert value == "test_value"
    
    configs = await config.list_configs("test_")
    assert "test_key" in configs
