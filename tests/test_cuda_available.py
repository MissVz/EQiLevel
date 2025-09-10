import pytest


# Skip the entire module if PyTorch is missing.
torch = pytest.importorskip("torch")


# Skip if CUDA is not available (CPU-only environments).
if not torch.cuda.is_available():
    pytest.skip("CUDA not available; skipping GPU tests.", allow_module_level=True)


def test_cuda_is_available():
    assert torch.cuda.is_available()


def test_cuda_matmul_small():
    # Small matmul to exercise the GPU without using much memory.
    x = torch.randn(256, 256, device="cuda")
    y = x @ x
    torch.cuda.synchronize()
    assert y.is_cuda
    assert y.shape == (256, 256)

