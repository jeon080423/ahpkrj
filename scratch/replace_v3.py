with open("G:\\ahp_utils_v3.py", "r", encoding="utf-8") as f:
    code = f.read()

# Replace any occurrence of ', _ = calculate_consistency'
code = code.replace(", _ = calculate_consistency", ", _unused = calculate_consistency")

with open("G:\\ahp_utils_v3.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Replacement complete!")
