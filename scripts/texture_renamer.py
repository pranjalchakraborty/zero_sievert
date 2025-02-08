import os
import re

mapping = {
    "fcount": "f",
    "xorg": "x",
    "yorg": "y",
    "bbox": "b"
}

def shorten_tokens(name):
    pattern = r"(fcount|xorg|yorg|bbox)(\d+)"
    def repl(m):
        token = m.group(1)
        number = m.group(2)
        if token == "fcount" and number == "0":
            return mapping[token] + "1"
        return mapping[token] + number
    return re.sub(pattern, repl, name)

def main():
    for filename in os.listdir('.'):
        if os.path.isfile(filename) and filename.endswith('.png'):
            base, ext = os.path.splitext(filename)
            new_base = shorten_tokens(base)
            new_filename = new_base + ext
            if new_filename != filename:
                print(f"Renaming '{filename}' to '{new_filename}'")
                os.rename(filename, new_filename)

if __name__ == '__main__':
    main()
    input("\nPress Enter to exit...")