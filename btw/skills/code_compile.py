from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from btw.skills.base import Skill


class CodeCompileSkill(Skill):
    """Writes a browser-loadable JS module wrapper for generated JSX."""

    name = "code_compile"
    description = "Compiles JSX into a JS module placeholder."

    async def execute(self, **kwargs) -> dict:
        jsx_code = kwargs.get("jsx_code", "")
        output_path = kwargs.get("output_path")

        if not jsx_code.strip():
            return {"success": False, "error": "empty code"}
        if not output_path:
            return {"success": False, "error": "missing output_path"}

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsx", encoding="utf-8", delete=False
        ) as handle:
            handle.write(jsx_code)
            source_path = Path(handle.name)

        try:
            esbuild = (
                Path(__file__).resolve().parents[1]
                / "frontend"
                / "node_modules"
                / ".bin"
                / "esbuild"
            )
            if not esbuild.exists():
                return {"success": False, "error": f"missing esbuild binary: {esbuild}"}

            result = subprocess.run(
                [
                    str(esbuild),
                    str(source_path),
                    "--format=cjs",
                    "--platform=browser",
                    "--loader:.jsx=jsx",
                    "--jsx-factory=React.createElement",
                    "--jsx-fragment=React.Fragment",
                    f"--outfile={output}",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                return {"success": False, "error": result.stderr or result.stdout}

            return {
                "success": True,
                "output_path": str(output),
                "bundle_size": output.stat().st_size,
            }
        finally:
            source_path.unlink(missing_ok=True)
