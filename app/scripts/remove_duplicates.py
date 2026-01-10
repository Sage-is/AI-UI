import json
from collections import OrderedDict
from pathlib import Path

def remove_duplicates(pairs):
    result = OrderedDict()
    for key, value in pairs:
        if key not in result:
            result[key] = value
    return result

def load_json_without_comments(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        # Remove lines starting with "//"
        lines = [line for line in f if not line.lstrip().startswith("//")]
    content = "".join(lines)
    # load using our duplicate-removing hook
    return json.loads(content, object_pairs_hook=remove_duplicates)

def main():
    locales_path = Path("../src/lib/i18n/locales")
    for translation_file in locales_path.rglob("translation.json"):
        data = load_json_without_comments(translation_file)
        with open(translation_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"Cleaned translation file: {translation_file}")

if __name__ == "__main__":
    main()