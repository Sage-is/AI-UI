import json
import sys
from pathlib import Path

def load_json_without_comments(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            # Remove lines that start with '//' (ignoring whitespace)
            lines = [line for line in f if not line.lstrip().startswith("//")]
        content = "".join(lines)
        try:
            json.loads(content)
            return None
        except json.JSONDecodeError as e:
            if "Expecting ',' delimiter" in e.msg:
                pos = e.pos
                corrected = content[:pos] + ',' + content[pos:]
                try:
                    json.loads(corrected)
                    # Write the corrected content back to the file.
                    with open(filepath, "w", encoding="utf-8") as f2:
                        f2.write(corrected)
                    print(f"Auto-fixed missing comma in {filepath}")
                    return None
                except Exception as e2:
                    return e2
            else:
                return e
    except Exception as e:
        return e

def main():
    # Adjust the base path as required; here we're scanning all JSON files in i18n locales.
    base_path = Path("../src/lib/i18n/locales")
    
    # Run the validation process up to 10 times
    for attempt in range(10):
        error_found = False
        print(f"Attempt {attempt + 1}...")
        for json_file in base_path.rglob("*.json"):
            error = load_json_without_comments(json_file)
            if error:
                print(f"Error in {json_file}: {error}")
                error_found = True
            else:
                # print(f"Valid: {json_file}")
                pass
        if not error_found:
            print("All JSON files are valid.")
            sys.exit(0)
        else:
            print("One or more JSON errors were found.")
    sys.exit(1)

if __name__ == "__main__":
    main()