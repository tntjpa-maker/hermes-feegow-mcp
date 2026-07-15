import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[3] / "data" / "knowledge"


class KnowledgeLoader:

    @classmethod
    def load(cls):

        root = json.loads((BASE_DIR / "clinic.json").read_text(encoding="utf-8"))

        knowledge = {}

        for filename in root.get("includes", []):

            file = BASE_DIR / filename

            if file.exists():

                try:
                    knowledge[file.stem] = json.loads(
                        file.read_text(encoding="utf-8")
                    )

                except Exception:
                    knowledge[file.stem] = {}

        return knowledge
