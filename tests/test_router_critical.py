"""Tests core/models/router.py : EzzioRouter + config."""
import pytest


def test_router_module_importable():
    from core.models import router as r
    assert r is not None


def test_router_has_ezzio_router_class():
    from core.models.router import EzzioRouter
    assert EzzioRouter is not None


def test_router_has_config_classes():
    from core.models.router import ModelConfig, RouterConfig
    assert ModelConfig is not None
    assert RouterConfig is not None


def test_router_has_routing_strategy():
    from core.models.router import RoutingStrategy
    assert hasattr(RoutingStrategy, "SIMPLE_SHUFFLE") or hasattr(RoutingStrategy, "__members__")


def test_router_has_request_type():
    from core.models.router import RequestType
    assert hasattr(RequestType, "__members__")
