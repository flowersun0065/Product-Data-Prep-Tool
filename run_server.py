#!/usr/bin/env python3
"""启动服务器（Web 或 Electron 模式）"""
import sys
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--electron', action='store_true', help='Run in Electron mode')
    parser.add_argument('--data-dir', type=str, default=None, help='App data directory')
    parser.add_argument('--host', type=str, default='127.0.0.1')
    parser.add_argument('--port', type=int, default=5001)
    args = parser.parse_args()

    if args.electron and args.data_dir:
        from product_cleaner.constants import BASE_DIR
        data_dir = Path(args.data_dir)
        for sub in ['brands', 'corrections', 'cache', 'categories', 'uploads', 'results']:
            (data_dir / sub).mkdir(parents=True, exist_ok=True)
            source = BASE_DIR / sub
            if source.exists():
                import shutil
                for f in source.iterdir():
                    dest = data_dir / sub / f.name
                    if not dest.exists() and f.is_file():
                        shutil.copy2(f, dest)
        import product_cleaner.constants as consts
        consts.BASE_DIR = data_dir

        from product_cleaner.web.app import set_electron_data_dir
        set_electron_data_dir(str(data_dir))

    from product_cleaner.web.app import app
    app.run(host=args.host, port=args.port, debug=False)

if __name__ == '__main__':
    main()
