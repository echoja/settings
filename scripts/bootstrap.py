#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.14"
# dependencies = ["typer>=0.21.0", "jsonschema>=4.23"]
# ///

from bootstrap import app

if __name__ == "__main__":
    app()
