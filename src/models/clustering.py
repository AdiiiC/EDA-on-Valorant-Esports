"""
Player Clustering — group players by playstyle using K-Means and DBSCAN.
"""

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans, DBSCAN
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score


PLAYSTYLE_FEATURES = ["acs", "kd", "adr", "kast", "kpr", "apr", "fkpr", "fdpr", "headshot_pct", "clutch_pct"]

PLAYSTYLE_LABELS = {
    0: "Entry Fragger",
    1: "Support/Anchor",
    2: "Aggressive Duelist",
    3: "Lurker/Clutch",
    4: "All-Rounder",
}


def prepare_features(df: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray, StandardScaler]:
    """Scale features for clustering."""
    features = df[PLAYSTYLE_FEATURES].copy()
    features = features.fillna(0)
    scaler = StandardScaler()
    scaled = scaler.fit_transform(features)
    return features, scaled, scaler


def find_optimal_k(scaled: np.ndarray, k_range: range = range(2, 8)) -> int:
    """Find optimal K via silhouette score."""
    best_k = 3
    best_score = -1
    for k in k_range:
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = km.fit_predict(scaled)
        score = silhouette_score(scaled, labels)
        if score > best_score:
            best_score = score
            best_k = k
    return best_k


def cluster_players_kmeans(df: pd.DataFrame, n_clusters: int = None) -> pd.DataFrame:
    """
    Cluster players into playstyle groups using K-Means.
    Returns df with 'cluster' and 'cluster_label' columns.
    """
    features, scaled, scaler = prepare_features(df)

    if n_clusters is None:
        n_clusters = find_optimal_k(scaled)

    km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = km.fit_predict(scaled)

    result = df.copy()
    result["cluster"] = labels
    result["cluster_label"] = result["cluster"].map(
        lambda x: PLAYSTYLE_LABELS.get(x, f"Group {x}")
    )
    return result


def cluster_players_dbscan(df: pd.DataFrame, eps: float = 1.2, min_samples: int = 3) -> pd.DataFrame:
    """
    Cluster players using DBSCAN — finds natural groupings + outliers.
    Outliers labeled as cluster -1.
    """
    features, scaled, scaler = prepare_features(df)

    db = DBSCAN(eps=eps, min_samples=min_samples)
    labels = db.fit_predict(scaled)

    result = df.copy()
    result["cluster"] = labels
    result["is_outlier"] = labels == -1
    return result


def get_pca_projection(df: pd.DataFrame, n_components: int = 2) -> pd.DataFrame:
    """Reduce player stats to 2D/3D for visualization."""
    features, scaled, scaler = prepare_features(df)

    pca = PCA(n_components=n_components)
    projected = pca.fit_transform(scaled)

    result = df[["player", "team"]].copy()
    for i in range(n_components):
        result[f"PC{i+1}"] = projected[:, i]

    result["explained_variance"] = sum(pca.explained_variance_ratio_[:n_components])
    return result, pca.explained_variance_ratio_


def get_cluster_profiles(df: pd.DataFrame) -> pd.DataFrame:
    """Get mean stats per cluster for profiling."""
    if "cluster" not in df.columns:
        return pd.DataFrame()
    return df.groupby("cluster")[PLAYSTYLE_FEATURES].mean().round(2)
