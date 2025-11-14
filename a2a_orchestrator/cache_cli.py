#!/usr/bin/env python3
"""CLI tool for managing A2A message cache."""

import sys
import argparse
from pathlib import Path

# Add repo root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from a2a_orchestrator.message_cache import A2AMessageCache


def main():
    parser = argparse.ArgumentParser(description="Manage A2A message cache")
    parser.add_argument(
        'command',
        choices=['stats', 'clear', 'invalidate'],
        help='Command to execute'
    )
    parser.add_argument(
        '--skill',
        help='Skill name for invalidate command'
    )
    
    args = parser.parse_args()
    
    cache = A2AMessageCache()
    
    if args.command == 'stats':
        stats = cache.get_stats()
        print("📊 A2A Message Cache Statistics")
        print("=" * 50)
        print(f"Total entries:    {stats['total_entries']}")
        print(f"Total cache hits: {stats['total_hits']}")
        print(f"Expired entries:  {stats['expired_entries']}")
        print(f"Cache size:       {stats['cache_size_mb']:.2f} MB")
        print("=" * 50)
        
    elif args.command == 'clear':
        cache.clear()
        print("✅ Cache cleared successfully")
        
    elif args.command == 'invalidate':
        if not args.skill:
            print("❌ Error: --skill required for invalidate command")
            sys.exit(1)
        cache.invalidate(args.skill)
        print(f"✅ Invalidated cache for skill: {args.skill}")


if __name__ == "__main__":
    main()
