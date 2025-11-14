#!/usr/bin/env python3
"""
Proxy Generator CLI - Generate printer-ready Magic card proxies from decklists.

Usage:
    python proxy_generator.py decklists/my_deck.txt
    python proxy_generator.py decklists/my_deck.txt --template custom.pptx
    python proxy_generator.py decklists/my_deck.txt --output my_proxies.pptx --no-pdf
"""
import argparse
import sys
import os
from pathlib import Path

import magic_cards


def main():
    """CLI entry point for proxy generation"""
    parser = argparse.ArgumentParser(
        description="Generate printer-ready Magic card proxies from decklists",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python proxy_generator.py decklists/krenko_mob_boss.txt
  python proxy_generator.py decklists/frog_tribal.txt --force
  python proxy_generator.py decklists/my_deck.txt --template custom_2v6h.pptx
  python proxy_generator.py decklists/my_deck.txt --output outputs/proxies.pptx --no-pdf
        """
    )

    # Positional arguments
    parser.add_argument(
        'decklist',
        help='Path to decklist file (one card per line, // for comments)'
    )

    # Optional arguments
    parser.add_argument(
        '--template',
        default='template_2v6h_FIXED.pptx',
        help='Path to template file (default: template_2v6h_FIXED.pptx)'
    )

    parser.add_argument(
        '--output',
        help='Output path for PPTX (default: outputs/<decklist_basename>.pptx)'
    )

    parser.add_argument(
        '--force',
        action='store_true',
        help='Force re-download of cards (ignore cache)'
    )

    parser.add_argument(
        '--no-pdf',
        action='store_true',
        help='Skip PDF conversion (only generate PPTX)'
    )

    args = parser.parse_args()

    # Validate inputs
    if not os.path.exists(args.decklist):
        print(f"❌ Error: Decklist not found: {args.decklist}")
        sys.exit(1)

    if not os.path.exists(args.template):
        print(f"❌ Error: Template not found: {args.template}")
        sys.exit(4)

    # Build output path
    if args.output:
        output_pptx = args.output
    else:
        decklist_name = Path(args.decklist).stem
        output_pptx = f"outputs/{decklist_name}.pptx"

    manifest_path = ".claude/state/fetch_manifest.json"

    print("🎴 Magic Card Proxy Generator")
    print("=" * 70)

    try:
        # Phase 1: Fetch card images
        print("\n📥 Phase 1: Fetching card images...")
        print("-" * 70)

        exit_code = magic_cards.fetch_resources_from_list(
            list_file=args.decklist,
            output_dir="images",
            manifest_path=manifest_path
        )

        # Check for complete failure
        if exit_code != 0:
            import json
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)

            if manifest['successful'] == 0:
                print("\n❌ Error: All cards failed to download")
                sys.exit(3)
            else:
                print(f"\n⚠️  Warning: {manifest['failed']}/{manifest['total_resources']} cards failed")

        # Phase 2: Generate presentation
        print("\n📐 Phase 2: Generating presentation...")
        print("-" * 70)

        try:
            magic_cards.generate_document(
                manifest_path=manifest_path,
                template_path=args.template,
                output_path=output_pptx
            )
        except ValueError as e:
            if "no valid" in str(e).lower():
                print(f"\n❌ Error: {e}")
                print("   Template must have rectangles ≥1.0\" × 1.0\"")
                sys.exit(4)
            raise

        # Phase 3: Convert to PDF
        if not args.no_pdf:
            print("\n📄 Phase 3: Converting to PDF...")
            print("-" * 70)

            try:
                pdf_path = magic_cards.transform_to_pdf(
                    source_path=output_pptx,
                    output_dir=None  # Same directory as PPTX
                )

                print("\n✅ Proxy generation complete!")
                print("=" * 70)
                print(f"📊 PPTX: {output_pptx}")
                print(f"📄 PDF:  {pdf_path}")

            except FileNotFoundError as e:
                if "LibreOffice" in str(e):
                    print(f"\n❌ Error: {e}")
                    sys.exit(5)
                raise
        else:
            print("\n✅ Proxy generation complete!")
            print("=" * 70)
            print(f"📊 PPTX: {output_pptx}")

        print("=" * 70)
        sys.exit(0)

    except FileNotFoundError as e:
        print(f"\n❌ Error: File not found: {e}")
        sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(130)

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
