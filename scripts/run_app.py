#!/usr/bin/env python3
"""Application Runner Script"""

import os
import sys
import argparse
from pathlib import Path

project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))


def run_app(port: int = 7860, host: str = "0.0.0.0", share: bool = False) -> bool:
    import runpy

    app_path = project_root / "src" / "apps" / "main_app_full.py"

    if not app_path.exists():
        print(f"❌ App file not found: {app_path}")
        return False

    print("🚀 Starting FBE Analytic System...")
    print(f"🌐 URL: http://{host}:{port}")

    os.chdir(project_root)
    os.environ["GRADIO_SERVER_NAME"] = host
    os.environ["GRADIO_SERVER_PORT"] = str(port)

    apps_path = project_root / "src" / "apps"
    sys.path.insert(0, str(apps_path))

    try:
        runpy.run_path(str(app_path), run_name="__main__")
        return True
    except KeyboardInterrupt:
        print("\n👋 Shutting down.")
        return True
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description="Run FBE Analytic System")
    parser.add_argument("--port", type=int, default=7860)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--share", action="store_true", help="Create public Gradio link")
    args = parser.parse_args()

    success = run_app(args.port, args.host, args.share)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
