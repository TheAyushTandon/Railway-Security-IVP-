import sys
import os
import json

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath("backend"))

from app.main import app

spec = app.openapi()
out_dir = os.path.abspath("contracts")
os.makedirs(out_dir, exist_ok=True)
out_file = os.path.join(out_dir, "openapi.json")

with open(out_file, "w", encoding="utf-8") as f:
    json.dump(spec, f, indent=2)

print(f"Exported OpenAPI spec to {out_file}")
