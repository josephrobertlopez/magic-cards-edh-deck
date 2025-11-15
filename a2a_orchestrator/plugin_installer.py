"""
Plugin Installer for Anthropic Skills Marketplace

Handles installation of skills from git-based marketplaces like anthropics/skills.
"""

import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass


# Hardcoded trusted marketplace registry
MARKETPLACES = {
    "anthropic-agent-skills": "https://github.com/anthropics/skills.git"
}


@dataclass
class PluginSpec:
    """
    Parsed plugin installation specification.

    Format: "skill-name@marketplace-name"
    """
    skill_name: str
    marketplace_name: str
    raw_spec: str

    @classmethod
    def parse(cls, spec: str) -> 'PluginSpec':
        """
        Parse plugin spec string.

        Args:
            spec: Format "skill-name@marketplace-name"

        Returns:
            PluginSpec instance

        Raises:
            ValueError: If spec format is invalid
        """
        if '@' not in spec:
            raise ValueError(
                f"Invalid plugin spec '{spec}'. Expected format: skill-name@marketplace-name"
            )

        parts = spec.split('@')
        if len(parts) != 2:
            raise ValueError(
                f"Invalid plugin spec '{spec}'. Must contain exactly one '@' separator"
            )

        skill_name, marketplace_name = parts

        # Validate skill name format (lowercase alphanumeric + hyphens)
        if not all(c.isalnum() or c == '-' for c in skill_name):
            raise ValueError(
                f"Invalid skill name '{skill_name}'. Must contain only lowercase letters, numbers, and hyphens"
            )

        return cls(
            skill_name=skill_name,
            marketplace_name=marketplace_name,
            raw_spec=spec
        )


class MarketplaceNotFoundError(Exception):
    """Raised when marketplace name is not in registry."""
    pass


class SkillNotFoundInMarketplaceError(Exception):
    """Raised when skill doesn't exist in marketplace repo."""
    pass


class InvalidSkillError(Exception):
    """Raised when skill is missing SKILL.md or has invalid frontmatter."""
    pass


class SkillExistsError(Exception):
    """Raised when skill already installed locally."""
    pass


class GitCommandError(Exception):
    """Raised when git command fails."""
    pass


class PluginInstaller:
    """
    Installs skills from marketplace repositories.

    Attributes:
        marketplace_registry: Dict mapping marketplace names to Git URLs
        target_dir: Destination directory for installed skills
    """

    def __init__(self, target_dir: Path = None, marketplace_registry: dict = None):
        """
        Initialize plugin installer.

        Args:
            target_dir: Where to install skills (default: .claude/skills/)
            marketplace_registry: Custom marketplace registry (default: MARKETPLACES)
        """
        self.target_dir = target_dir or Path(".claude/skills")
        self.marketplace_registry = marketplace_registry or MARKETPLACES

    def install(self, plugin_spec: str) -> Path:
        """
        Install skill from marketplace.

        Args:
            plugin_spec: Format "skill-name@marketplace-name"

        Returns:
            Path to installed skill directory

        Raises:
            MarketplaceNotFoundError: Invalid marketplace name
            SkillNotFoundInMarketplaceError: Skill doesn't exist in marketplace
            InvalidSkillError: SKILL.md missing or invalid frontmatter
            SkillExistsError: Skill already installed locally
            GitCommandError: Git clone failed
        """
        # Parse plugin spec
        spec = PluginSpec.parse(plugin_spec)

        # Validate marketplace exists
        if spec.marketplace_name not in self.marketplace_registry:
            available = ", ".join(self.marketplace_registry.keys())
            raise MarketplaceNotFoundError(
                f"Marketplace '{spec.marketplace_name}' not found. "
                f"Available marketplaces: {available}"
            )

        repo_url = self.marketplace_registry[spec.marketplace_name]

        # Check if skill already installed
        dest_path = self.target_dir / spec.skill_name
        if dest_path.exists():
            raise SkillExistsError(
                f"Skill '{spec.skill_name}' already installed at {dest_path}"
            )

        # Clone marketplace repo to temp directory
        with tempfile.TemporaryDirectory() as tmp_dir:
            clone_dir = Path(tmp_dir) / "marketplace"

            print(f"🔄 Cloning marketplace {spec.marketplace_name}...")
            try:
                subprocess.run(
                    ["git", "clone", "--depth", "1", repo_url, str(clone_dir)],
                    check=True,
                    capture_output=True,
                    text=True
                )
            except subprocess.CalledProcessError as e:
                raise GitCommandError(
                    f"Failed to clone marketplace: {e.stderr}"
                )
            except FileNotFoundError:
                raise GitCommandError(
                    "Git command not found. Please install git: https://git-scm.com/downloads"
                )

            # Find skill directory
            skill_source = clone_dir / spec.skill_name
            if not skill_source.exists():
                raise SkillNotFoundInMarketplaceError(
                    f"Skill '{spec.skill_name}' not found in marketplace '{spec.marketplace_name}'"
                )

            # Validate SKILL.md exists
            skill_md = skill_source / "SKILL.md"
            if not skill_md.exists():
                raise InvalidSkillError(
                    f"Skill '{spec.skill_name}' missing SKILL.md file"
                )

            # Validate frontmatter
            if not self.validate_skill(skill_source):
                raise InvalidSkillError(
                    f"Skill '{spec.skill_name}' has invalid SKILL.md frontmatter"
                )

            # Copy to .claude/skills/
            self.target_dir.mkdir(parents=True, exist_ok=True)
            shutil.copytree(skill_source, dest_path)

            print(f"✅ Installed '{spec.skill_name}' to {dest_path}")
            return dest_path

    def validate_skill(self, skill_path: Path) -> bool:
        """
        Verify SKILL.md structure and frontmatter.

        Args:
            skill_path: Path to skill directory

        Returns:
            True if valid, False otherwise
        """
        skill_md = skill_path / "SKILL.md"
        if not skill_md.exists():
            return False

        try:
            import frontmatter

            with open(skill_md, 'r', encoding='utf-8-sig') as f:
                post = frontmatter.load(f)

            # Check required fields
            if 'name' not in post.metadata:
                print(f"⚠️  Missing 'name' in frontmatter")
                return False
            if 'description' not in post.metadata:
                print(f"⚠️  Missing 'description' in frontmatter")
                return False

            return True

        except Exception as e:
            print(f"⚠️  Validation error: {e}")
            return False

    def list_available(self, marketplace: str) -> list:
        """
        List skills available in marketplace.

        Args:
            marketplace: Marketplace name

        Returns:
            List of skill names

        Raises:
            MarketplaceNotFoundError: Invalid marketplace
            GitCommandError: Clone failed
        """
        if marketplace not in self.marketplace_registry:
            available = ", ".join(self.marketplace_registry.keys())
            raise MarketplaceNotFoundError(
                f"Marketplace '{marketplace}' not found. "
                f"Available: {available}"
            )

        repo_url = self.marketplace_registry[marketplace]

        with tempfile.TemporaryDirectory() as tmp_dir:
            clone_dir = Path(tmp_dir) / "marketplace"

            try:
                subprocess.run(
                    ["git", "clone", "--depth", "1", repo_url, str(clone_dir)],
                    check=True,
                    capture_output=True,
                    text=True
                )
            except subprocess.CalledProcessError as e:
                raise GitCommandError(f"Failed to clone: {e.stderr}")

            # List directories containing SKILL.md
            skills = []
            for item in clone_dir.iterdir():
                if item.is_dir() and (item / "SKILL.md").exists():
                    skills.append(item.name)

            return sorted(skills)
