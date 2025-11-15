#!/usr/bin/env python3
"""
CLI interface for plugin management.

Usage:
    python -m a2a_orchestrator.cli.plugin install skill-name@marketplace-name
    python -m a2a_orchestrator.cli.plugin list anthropic-agent-skills
"""

import sys
from pathlib import Path

# Add repo root to path
repo_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(repo_root))

from a2a_orchestrator.plugin_installer import (
    PluginInstaller,
    MarketplaceNotFoundError,
    SkillNotFoundInMarketplaceError,
    InvalidSkillError,
    SkillExistsError,
    GitCommandError
)


def main():
    """CLI entry point for plugin commands."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python -m a2a_orchestrator.cli.plugin install <skill@marketplace>")
        print("  python -m a2a_orchestrator.cli.plugin list <marketplace>")
        print("")
        print("Examples:")
        print("  python -m a2a_orchestrator.cli.plugin install document-skills@anthropic-agent-skills")
        print("  python -m a2a_orchestrator.cli.plugin list anthropic-agent-skills")
        sys.exit(1)

    command = sys.argv[1]
    installer = PluginInstaller()

    if command == "install":
        if len(sys.argv) < 3:
            print("❌ Error: Missing plugin spec")
            print("Usage: python -m a2a_orchestrator.cli.plugin install <skill@marketplace>")
            sys.exit(1)

        plugin_spec = sys.argv[2]

        try:
            installed_path = installer.install(plugin_spec)
            print(f"🎉 Successfully installed plugin!")
            print(f"📂 Location: {installed_path}")
            print(f"✅ Ready to use in workflows")

        except MarketplaceNotFoundError as e:
            print(f"❌ {e}")
            sys.exit(1)
        except SkillNotFoundInMarketplaceError as e:
            print(f"❌ {e}")
            sys.exit(1)
        except InvalidSkillError as e:
            print(f"❌ {e}")
            sys.exit(1)
        except SkillExistsError as e:
            print(f"⚠️  {e}")
            sys.exit(1)
        except GitCommandError as e:
            print(f"❌ Git error: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            sys.exit(1)

    elif command == "list":
        if len(sys.argv) < 3:
            print("❌ Error: Missing marketplace name")
            print("Usage: python -m a2a_orchestrator.cli.plugin list <marketplace>")
            sys.exit(1)

        marketplace = sys.argv[2]

        try:
            skills = installer.list_available(marketplace)
            print(f"📦 Available skills in '{marketplace}':")
            for skill in skills:
                print(f"  - {skill}")
            print(f"\n📝 To install: python -m a2a_orchestrator.cli.plugin install <skill>@{marketplace}")

        except MarketplaceNotFoundError as e:
            print(f"❌ {e}")
            sys.exit(1)
        except GitCommandError as e:
            print(f"❌ Git error: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            sys.exit(1)

    else:
        print(f"❌ Unknown command: {command}")
        print("Available commands: install, list")
        sys.exit(1)


if __name__ == "__main__":
    main()
