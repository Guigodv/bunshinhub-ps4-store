#!/usr/bin/env python3
"""Preflight for BunshinHub's native PS4 package configuration."""
from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TITLE_ID = "BUNSH0001"

def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--after-build", action="store_true")
    args = parser.parse_args()

    makefile = (ROOT / "Store/Makefile").read_text()
    package_xml = ET.parse(ROOT / "Store/pkg.gp4").getroot()
    def variable(name: str) -> str:
        found = re.search(rf"^{re.escape(name)}\s*:=\s*(\S+)\s*$", makefile, re.MULTILINE)
        if not found:
            fail(f"Missing Makefile variable {name}")
        return found.group(1)

    title_id = variable("TITLE_ID")
    content_id = variable("CONTENT_ID")
    if title_id != TITLE_ID:
        fail(f"Unexpected TITLE_ID: {title_id}")
    if not re.fullmatch(r"[A-Z0-9]{9}", title_id):
        fail(f"Invalid PS4 Title ID: {title_id}")
    if not re.fullmatch(r"[A-Z0-9]{6}-[A-Z0-9]{9}_00-[A-Z0-9]{16}", content_id):
        fail(f"Invalid CONTENT_ID: {content_id}")

    package = package_xml.find("./volume/package")
    if package is None or package.get("content_id") != content_id:
        fail("Makefile and pkg.gp4 CONTENT_ID values do not match")

    assets = package_xml.findall("./files/file")
    if not assets:
        fail("No files listed in pkg.gp4")
    generated = {
        "sce_sys/param.sfo",
        "homebrew.elf",
        "../Store-Loader/eboot.bin",
    }
    missing = []
    for asset in assets:
        source = asset.get("orig_path")
        if not source:
            fail("A GP4 entry has no orig_path")
        if args.after_build or source not in generated:
            if not (ROOT / "Store" / source).is_file():
                missing.append(source)
    if missing:
        fail(f"Missing GP4 assets: {', '.join(missing[:12])}")

    native_files = [
        "Store-Loader/source/main.c", "Store-Loader/source/app.c",
        "Store/source/common_init.cpp", "Store/source/utils.cpp",
        "Store/source/GLES2_scene_v2.cpp", "Store/source/sql.cpp",
        "Store/include/defines.h", "Store/include/utils.h",
    ]
    for path in native_files:
        if "NPXS39041" in (ROOT / path).read_text():
            fail(f"Original PS4-Store Title ID remains in {path}")

    print(f"PASS: {variable('TITLE')} ({title_id}), content ID {content_id}")
    print(f"PASS: {len(assets)} packaged files resolved")
    print("PASS: native code paths use BunshinHub Title ID")

if __name__ == "__main__":
    main()
