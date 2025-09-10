import sys


def main() -> int:
    try:
        import torch  # type: ignore
    except Exception as e:
        print(f"FAIL: Could not import torch: {e}")
        print("Hint: Activate the correct venv and install requirements.")
        return 1

    torch_ver = getattr(torch, "__version__", "?")
    cuda_built = getattr(getattr(torch, "version", None), "cuda", None)
    cudnn_ver = (
        str(torch.backends.cudnn.version()) if torch.backends.cudnn.is_available() else "N/A"
    )

    print(f"Torch: {torch_ver} | CUDA runtime: {cuda_built} | cuDNN: {cudnn_ver}")

    available = torch.cuda.is_available()
    print(f"CUDA available: {available}")
    if not available:
        print("FAIL: torch.cuda.is_available() is False.")
        print("Hint: Ensure GPU wheels (e.g., +cu118/+cu121) and recent NVIDIA driver.")
        return 1

    try:
        count = torch.cuda.device_count()
        print(f"GPU count: {count}")
        for i in range(count):
            name = torch.cuda.get_device_name(i)
            props = torch.cuda.get_device_properties(i)
            mem_gb = props.total_memory / (1024**3)
            print(f" - GPU {i}: {name} | CC {props.major}.{props.minor} | {mem_gb:.1f} GB")

        # Simple CUDA compute test
        x = torch.randn(1024, 1024, device="cuda")
        y = x @ x
        _ = y.norm().item()
        torch.cuda.synchronize()
        print("CUDA matmul: OK")
        return 0
    except Exception as e:
        print(f"FAIL: CUDA compute failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

