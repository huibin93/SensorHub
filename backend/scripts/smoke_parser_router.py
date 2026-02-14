"""Smoke script: print parser facade routing result."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import settings
from app.services import parser as parser_facade


def main() -> None:
    resolved = parser_facade._resolve_parser_impl()
    impl_cls = parser_facade._get_impl_class()
    print(f"PARSER_IMPL={getattr(settings, 'PARSER_IMPL', '<missing>')}")
    print(f"resolved_impl={resolved}")
    print(f"target_class={impl_cls.__module__}.{impl_cls.__name__}")


if __name__ == "__main__":
    main()
