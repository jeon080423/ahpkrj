import os
import numpy as np

# Ensure the project directory is in sys.path
import sys
project_root = r"k:/app/4. AHP마스터"
if project_root not in sys.path:
    sys.path.append(project_root)

from cr_analysis import run_analysis, generate_report

def generate_random_matrix(n, consistency=0.8):
    rng = np.random.default_rng()
    a = rng.random((n, n))
    a = (a + a.T) / 2
    np.fill_diagonal(a, 1.0)
    a = consistency * a + (1 - consistency) * np.ones((n, n))
    return a

original = generate_random_matrix(4, consistency=0.85)
# Simulate a corrected matrix by adding slight noise
corrected = original * 1.02
metrics = run_analysis(original, corrected, "Sample Correction")
report_html = generate_report([metrics], original, {"Sample Correction": corrected})
# Save the report in the project folder for easy access
output_path = os.path.join(project_root, "cr_sample_report.html")
with open(output_path, "w", encoding="utf-8") as f:
    f.write(report_html)
print(f"Report written to {output_path}")
