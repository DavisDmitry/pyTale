from pytale.plugin import (
    get_context,
    get_data_directory,
    get_identifier,
    get_manifest,
    on_setup,
    on_shutdown,
    on_start,
)

print("=" * 60)
print("pyTale Plugin Information")
print("=" * 60)

identifier = get_identifier()
print(f"\nIdentifier:")
print(f"  Group: {identifier.group}")
print(f"  Name: {identifier.name}")

manifest = get_manifest()
print(f"\nManifest:")
print(f"  Name: {manifest.name}")
print(f"  Version: {manifest.version}")
print(f"  Description: {manifest.description}")
print(f"  Authors: {manifest.authors}")
print(f"  Website: {manifest.website}")

data_dir = get_data_directory()
print(f"\nData Directory: {data_dir}")

context = get_context()
print(f"\nExecution Context: {context.name} ({context.value})")

print("\n" + "=" * 60)


@on_setup
def on_plugin_setup() -> None:
    print("[LIFECYCLE] Plugin setup!")


@on_start
def on_plugin_start() -> None:
    print("[LIFECYCLE] Plugin started!")


@on_shutdown
def on_plugin_shutdown() -> None:
    print("[LIFECYCLE] Plugin shutting down!")
