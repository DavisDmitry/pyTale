"""CLI interface for pytale-tools"""

import argparse
import sys
from pathlib import Path

from pytale_tools.builder import PluginBuilder


def create_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser"""
    parser = argparse.ArgumentParser(
        prog="pytale-tools", description="PyTale development tools"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Build command
    build_parser = subparsers.add_parser("build", help="Build a Python plugin JAR")
    build_parser.add_argument(
        "source",
        type=Path,
        help="Path to wheel file (.whl) or plugin project directory",
    )
    build_parser.add_argument(
        "-o", "--output", type=Path, help="Output JAR path (default: plugin-name.jar)"
    )
    build_parser.add_argument(
        "-r",
        "--requirements",
        type=Path,
        help="Optional: path to requirements.txt for plugin dependencies (versions must be pinned with ==)",
    )
    build_parser.add_argument(
        "--download-workers",
        type=int,
        default=10,
        help="Maximum number of parallel PyPI download workers (default: 10)",
    )

    # Export command
    export_parser = subparsers.add_parser(
        "export", help="Export class metadata from a Java JAR to JSON"
    )
    export_parser.add_argument("jar", type=Path, help="Path to Java JAR file")
    export_parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("."),
        help="Output directory (default: current directory)",
    )
    export_parser.add_argument(
        "-t",
        "--target",
        choices=["all", "events", "components"],
        default="all",
        help="What to export (default: all)",
    )

    # Generate command
    generate_parser = subparsers.add_parser(
        "generate", help="Generate Python wrapper classes from a JAR or exported JSON"
    )
    generate_parser.add_argument(
        "source", type=Path, help="Path to Java JAR file or exported JSON"
    )
    generate_parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("generated"),
        help="Output directory for generated files (default: ./generated/)",
    )
    generate_parser.add_argument(
        "-t",
        "--target",
        choices=["all", "events", "components"],
        default="all",
        help="What to generate (default: all)",
    )

    return parser


def main() -> int:
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    try:
        if args.command == "build":
            builder = PluginBuilder(
                args.source,
                args.requirements,
                max_workers=args.download_workers,
            )
            output = args.output or Path(f"{builder.metadata['name']}.jar")
            builder.build(output)
        elif args.command == "export":
            from pytale_tools.exporter import ExportTarget, export_to_json

            export_target = ExportTarget(args.target)
            print(f"Exporting {export_target.value} from {args.jar.name}...")
            written = export_to_json(args.jar, args.output, export_target)
            for path in written:
                print(f"  {path}")
            print("Done!")
        elif args.command == "generate":
            from pytale_tools.generator import GenerateTarget, generate

            generate_target = GenerateTarget(args.target)
            print(f"Generating wrappers from {args.source.name}...")
            generate(args.source, args.output, generate_target)
            print(f"Done! Output: {args.output}/")
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
