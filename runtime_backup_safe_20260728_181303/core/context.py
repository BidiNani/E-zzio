from runtime.contracts.execution_context import ExecutionContext


try:
    from runtime.contracts.capability import TokenSigner
except ImportError:
    pass
