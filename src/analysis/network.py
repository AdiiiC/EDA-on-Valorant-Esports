"""
Network Analysis — player-team graphs, co-play networks, transfer flows.
"""

import pandas as pd
import networkx as nx
from dataclasses import dataclass


@dataclass
class NetworkMetrics:
    nodes: int
    edges: int
    density: float
    most_connected: list[tuple[str, int]]
    communities: int


def build_transfer_network(transfers_df: pd.DataFrame) -> nx.DiGraph:
    """
    Build directed graph of player transfers between teams.
    Nodes = teams, edges = transfers (weighted by count).
    """
    G = nx.DiGraph()

    for _, row in transfers_df.iterrows():
        old = row["old_team"]
        new = row["new_team"]
        if old and new and old != "Free Agent" and new != "Free Agent":
            if G.has_edge(old, new):
                G[old][new]["weight"] += 1
                G[old][new]["players"].append(row["player"])
            else:
                G.add_edge(old, new, weight=1, players=[row["player"]])

    return G


def build_coplay_network(player_stats_df: pd.DataFrame) -> nx.Graph:
    """
    Build undirected graph where players on the same team are connected.
    Edge weight = shared team (proxy for playing together).
    """
    G = nx.Graph()

    teams = player_stats_df.groupby("team")["player"].apply(list).to_dict()

    for team, players in teams.items():
        for i, p1 in enumerate(players):
            G.add_node(p1, team=team)
            for p2 in players[i + 1:]:
                G.add_node(p2, team=team)
                if G.has_edge(p1, p2):
                    G[p1][p2]["weight"] += 1
                else:
                    G.add_edge(p1, p2, weight=1, team=team)

    return G


def build_player_team_bipartite(transfers_df: pd.DataFrame) -> nx.Graph:
    """
    Bipartite graph: players <-> teams they've been on.
    Useful for finding players with most team affiliations.
    """
    G = nx.Graph()

    for _, row in transfers_df.iterrows():
        player = row["player"]
        G.add_node(player, bipartite=0, node_type="player")

        for team in [row["old_team"], row["new_team"]]:
            if team and team != "Free Agent":
                G.add_node(team, bipartite=1, node_type="team")
                G.add_edge(player, team)

    return G


def get_network_metrics(G: nx.Graph) -> NetworkMetrics:
    """Compute basic network metrics."""
    if len(G) == 0:
        return NetworkMetrics(0, 0, 0.0, [], 0)

    degree_centrality = nx.degree_centrality(G)
    top_nodes = sorted(degree_centrality.items(), key=lambda x: x[1], reverse=True)[:10]
    most_connected = [(node, G.degree(node)) for node, _ in top_nodes]

    # Community detection (undirected only)
    n_communities = 0
    if not G.is_directed():
        try:
            communities = nx.community.louvain_communities(G, seed=42)
            n_communities = len(communities)
        except Exception:
            n_communities = 0

    return NetworkMetrics(
        nodes=len(G.nodes),
        edges=len(G.edges),
        density=round(nx.density(G), 4),
        most_connected=most_connected,
        communities=n_communities,
    )


def get_transfer_flow_data(transfers_df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare Sankey diagram data for transfer flows between teams.
    Returns DataFrame with source, target, value columns.
    """
    if transfers_df.empty:
        return pd.DataFrame(columns=["source", "target", "value"])

    flows = transfers_df.groupby(["old_team", "new_team"]).size().reset_index(name="value")
    flows = flows[
        (flows["old_team"] != "Free Agent") &
        (flows["new_team"] != "Free Agent") &
        (flows["old_team"] != "") &
        (flows["new_team"] != "")
    ]
    flows.columns = ["source", "target", "value"]
    flows = flows.sort_values("value", ascending=False)

    return flows


def get_team_centrality_rankings(transfers_df: pd.DataFrame) -> pd.DataFrame:
    """Rank teams by centrality in the transfer network (most involved in market)."""
    G = build_transfer_network(transfers_df)

    if len(G) == 0:
        return pd.DataFrame(columns=["team", "in_degree", "out_degree", "betweenness"])

    in_deg = dict(G.in_degree(weight="weight"))
    out_deg = dict(G.out_degree(weight="weight"))
    betweenness = nx.betweenness_centrality(G, weight="weight")

    data = []
    for node in G.nodes:
        data.append({
            "team": node,
            "in_degree": in_deg.get(node, 0),
            "out_degree": out_deg.get(node, 0),
            "net_flow": in_deg.get(node, 0) - out_deg.get(node, 0),
            "betweenness": round(betweenness.get(node, 0), 4),
        })

    df = pd.DataFrame(data)
    df = df.sort_values("betweenness", ascending=False).reset_index(drop=True)
    return df


def find_super_team_candidates(player_stats_df: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
    """
    Identify potential 'super team' by selecting top players from different roles.
    Uses high ACS + high FKPR for entry, high KAST + APR for support, etc.
    """
    if player_stats_df.empty:
        return pd.DataFrame()

    df = player_stats_df.copy()

    # Role heuristics based on stats
    df["entry_score"] = df["fkpr"] * 0.4 + df["acs"] * 0.003 + df["kpr"] * 0.3
    df["support_score"] = df["apr"] * 0.4 + df["kast"] * 0.01 + (1 - df["fdpr"]) * 0.2
    df["clutch_score"] = df["clutch_pct"] * 0.01 + df["kd"] * 0.3 + df["adr"] * 0.002

    # Pick top for each role
    entries = df.nlargest(top_n, "entry_score")[["player", "team", "entry_score"]].copy()
    entries["role"] = "Entry Fragger"
    entries.rename(columns={"entry_score": "role_score"}, inplace=True)

    supports = df.nlargest(top_n, "support_score")[["player", "team", "support_score"]].copy()
    supports["role"] = "Support"
    supports.rename(columns={"support_score": "role_score"}, inplace=True)

    clutchers = df.nlargest(top_n, "clutch_score")[["player", "team", "clutch_score"]].copy()
    clutchers["role"] = "Clutch/Lurk"
    clutchers.rename(columns={"clutch_score": "role_score"}, inplace=True)

    candidates = pd.concat([entries, supports, clutchers], ignore_index=True)
    candidates["role_score"] = candidates["role_score"].round(3)

    return candidates
