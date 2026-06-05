import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import io
import base64

def euclidean_distance(a: np.ndarray, b: np.ndarray) -> float:
    return np.linalg.norm(a - b)

def manhattan_distance(a: np.ndarray, b: np.ndarray) -> float:
    return np.abs(a - b).sum()

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    dot = np.dot(a.ravel(), b.ravel())
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)

def distortion_score(eu_dist: float, man_dist: float) -> float:
    # Normalize using simple min-max on a reasonable range (0, 1) for demo
    # Here we just average the two distances after scaling by matrix size
    return (eu_dist + man_dist) / 2.0

def run_analysis(original_matrix: np.ndarray, corrected_matrix: np.ndarray, option_name: str) -> dict:
    """Calculate metrics comparing original and corrected matrices.

    Parameters
    ----------
    original_matrix : np.ndarray
        The matrix before CR correction.
    corrected_matrix : np.ndarray
        The matrix after CR correction.
    option_name : str
        Human‑readable name of the CR option (e.g., "Do Not Correct", "0.1", "0.2").

    Returns
    -------
    dict
        A dictionary containing distance metrics, cosine similarity, and a composite
        distortion score.
    """
    eu = euclidean_distance(original_matrix, corrected_matrix)
    man = manhattan_distance(original_matrix, corrected_matrix)
    cos = cosine_similarity(original_matrix, corrected_matrix)
    dist = distortion_score(eu, man)
    return {
        "option": option_name,
        "euclidean": eu,
        "manhattan": man,
        "cosine_similarity": cos,
        "distortion_score": dist,
    }

def matrix_to_heatmap_img(matrix: np.ndarray, title: str = "Matrix Heatmap") -> str:
    """Return a base64‑encoded PNG of a heatmap for the given matrix.
    The string can be embedded in HTML via `<img src="data:image/png;base64,{data}">`.
    """
    plt.figure(figsize=(5, 4))
    sns.heatmap(matrix, cmap="viridis", annot=False, cbar=True)
    plt.title(title)
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close()
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")

def generate_report(metrics: list[dict], original_matrix: np.ndarray, corrected_matrices: dict[str, np.ndarray]) -> str:
    """Create an HTML report summarizing the CR analysis.

    Parameters
    ----------
    metrics : list[dict]
        List of metric dictionaries returned by ``run_analysis``.
    original_matrix : np.ndarray
        The uncorrected matrix.
    corrected_matrices : dict[str, np.ndarray]
        Mapping from option name to its corrected matrix.
    """
    rows_html = "".join(
        f"<tr><td>{m['option']}</td><td>{m['euclidean']:.4f}</td><td>{m['manhattan']:.4f}</td><td>{m['cosine_similarity']:.4f}</td><td>{m['distortion_score']:.4f}</td></tr>"
        for m in metrics
    )
    # Heatmaps for original and each corrected matrix
    orig_img = matrix_to_heatmap_img(original_matrix, "Original Matrix")
    corrected_imgs = "".join(
        f"<h4>{opt}</h4><img src='data:image/png;base64,{matrix_to_heatmap_img(mat, opt)}' style='max-width:100%; height:auto;'>"
        for opt, mat in corrected_matrices.items()
    )
    html = f"""
<!DOCTYPE html>
<html lang='en'>
<head>
<meta charset='UTF-8'>
<title>CR Analysis Report</title>
<style>
  body {{ font-family: Arial, sans-serif; background: #f9f9f9; padding: 20px; }}
  table {{ border-collapse: collapse; width: 100%; background: #fff; }}
  th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
  th {{ background-color: #4a90e2; color: white; }}
  h2 {{ color: #333; }}
</style>
</head>
<body>
<h2>Consistency Ratio (CR) Correction Analysis</h2>
<h3>Summary Table</h3>
<table>
<tr><th>Option</th><th>Euclidean</th><th>Manhattan</th><th>Cosine Sim.</th><th>Distortion Score</th></tr>
{rows_html}
</table>
<h3>Heatmaps</h3>
<h4>Original Matrix</h4>
<img src='data:image/png;base64,{orig_img}' style='max-width:100%; height:auto;'>
{corrected_imgs}
</body>
</html>
"""
    return html
