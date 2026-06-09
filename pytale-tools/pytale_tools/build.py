"""Plugin builder for PyTale"""

import shutil
import tempfile
import tomllib
import zipfile
from pathlib import Path
from typing import Dict


class PluginBuilder:
    def __init__(self, plugin_dir: Path):
        self.plugin_dir = plugin_dir.resolve()
        self.pyproject_path = self.plugin_dir / "pyproject.toml"
        self.metadata = self._read_metadata()

    def _read_metadata(self) -> Dict:
        if not self.pyproject_path.exists():
            raise FileNotFoundError(f"pyproject.toml not found in {self.plugin_dir}")

        with open(self.pyproject_path, "rb") as f:
            data = tomllib.load(f)

        project = data.get("project", {})
        return {
            "name": project.get("name", self.plugin_dir.name),
            "version": project.get("version", "1.0.0"),
            "description": project.get("description", ""),
        }

    def _copy_loader_class(self, temp_dir: Path) -> str:
        """Copy pre-compiled PythonPlugin.class from resources"""
        class_file = self._find_python_plugin_class()
        if not class_file.exists():
            raise FileNotFoundError(
                f"PythonPlugin.class not found at {class_file}. "
                f"Build PyTale first with: ./gradlew jar"
            )

        # Create package directory structure
        pkg_dir = temp_dir / "dev" / "taledale" / "pytale"
        pkg_dir.mkdir(parents=True, exist_ok=True)

        # Copy class file to temp directory
        import shutil
        shutil.copy2(class_file, pkg_dir / "PythonPlugin.class")

        return "dev.taledale.pytale.PythonPlugin"

    def _find_python_plugin_class(self) -> Path:
        """Find pre-extracted PythonPlugin.class in pytale-tools resources"""
        pytale_tools_dir = Path(__file__).parent
        return pytale_tools_dir / "resources" / "PythonPlugin.class"

    def _create_manifest_json(self, temp_dir: Path) -> Path:
        """Create manifest.json for Hytale"""
        import json

        manifest_path = temp_dir / "manifest.json"
        manifest = {
            "Group": "TaleDale",
            "Name": self.metadata["name"],
            "Version": self.metadata["version"],
            "Authors": [],
            "DisabledByDefault": False,
            "IncludesAssetPack": False,
            "Dependencies": {"TaleDale:PyTale": ">=0.0.1"},
            "OptionalDependencies": {},
            "ServerVersion": "=0.5.3",
            "Main": "dev.taledale.pytale.PythonPlugin",
        }
        manifest_path.write_text(json.dumps(manifest, indent=4))
        return manifest_path

    def _copy_python_code(self, temp_dir: Path):
        """Copy Python code to python/<module_name>/ directory"""
        plugin_name = self.metadata["name"].replace("-", "_")
        plugin_pkg = self.plugin_dir / plugin_name
        python_dir = temp_dir / "python" / plugin_name
        python_dir.mkdir(parents=True, exist_ok=True)

        if plugin_pkg.exists() and (plugin_pkg / "__init__.py").exists():
            for item in plugin_pkg.rglob("*"):
                relative = item.relative_to(plugin_pkg)
                dest = python_dir / relative
                if item.is_file():
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dest)
        else:
            raise FileNotFoundError(
                f"Python package not found. Expected: {plugin_pkg} with __init__.py"
            )

        if not list(python_dir.rglob("*.py")):
            raise FileNotFoundError(f"No .py files found in {plugin_pkg}")

    def _copy_venv(self, temp_dir: Path):
        """Copy .venv if it exists"""
        venv_src = self.plugin_dir / ".venv"
        if venv_src.exists():
            venv_dst = temp_dir / ".venv"
            shutil.copytree(venv_src, venv_dst)

    def _create_jar(self, temp_dir: Path, output_path: Path) -> Path:
        """Create JAR from temp directory, excluding build artifacts"""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Directories to exclude from JAR
        exclude_dirs = {"src", "classes"}

        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as jar:
            for item in temp_dir.rglob("*"):
                if item.is_file():
                    # Skip files in excluded directories
                    parts = item.relative_to(temp_dir).parts
                    if parts and parts[0] in exclude_dirs:
                        continue
                    arcname = str(item.relative_to(temp_dir))
                    jar.write(item, arcname=arcname)

        return output_path

    def build(self, output_path: Path) -> Path:
        """Build plugin JAR"""
        output_path = output_path.resolve()

        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)

            # Copy universal PythonPlugin loader class from pytale.jar
            self._copy_loader_class(temp_dir)

            # Create manifest.json
            self._create_manifest_json(temp_dir)

            # Copy Python code
            self._copy_python_code(temp_dir)

            # Copy .venv if exists
            self._copy_venv(temp_dir)

            # Create JAR
            self._create_jar(temp_dir, output_path)

            print(f"✓ Plugin JAR created: {output_path}")
            return output_path
