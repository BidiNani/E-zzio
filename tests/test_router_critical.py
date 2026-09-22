"""Tests core/models/ezzio_router.py : EzzioRouter + re-export des types."""
import pytest


def test_router_module_importable():
    from core.models import ezzio_router as r
    assert r is not None


def test_router_has_ezzio_router_class():
    from core.models.ezzio_router import EzzioRouter
    assert EzzioRouter is not None


def test_router_has_config_classes():
    from core.models._dormant_litellm_types import ModelConfig, RouterConfig
    assert ModelConfig is not None
    assert RouterConfig is not None


def test_router_has_routing_strategy():
    from core.models._dormant_litellm_types import RoutingStrategy
    assert hasattr(RoutingStrategy, "SIMPLE_SHUFFLE") or hasattr(RoutingStrategy, "__members__")


def test_router_has_request_type():
    from core.models._dormant_litellm_types import RequestType
    assert hasattr(RequestType, "__members__")
