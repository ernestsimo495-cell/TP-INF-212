"""
=============================================================================
 graphe.py — Groupe A : Structure du Graphe & Visualisation
 Projet : Planification d'Examens par Coloration de Graphes
 Niveau : L2 Informatique — Théorie des Graphes
=============================================================================

Ce fichier implémente :
  1. Le chargement des données (UE, étudiants, inscriptions)
  2. La construction du graphe de conflits
     - Matrice d'adjacence
     - Liste d'adjacence
  3. Le calcul des descripteurs du graphe
     - Nombre de sommets, d'arêtes, degrés de chaque sommet
  4. La visualisation du graphe avec networkx + matplotlib
     → Génère un fichier PNG : graphe_conflits.png

=============================================================================
"""

import csv
import os
import time
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")          # rendu sans interface graphique
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import networkx as nx


# ─────────────────────────────────────────────────────────────────────────────
# 1.  CHARGEMENT DES DONNÉES
# ─────────────────────────────────────────────────────────────────────────────

def charger_donnees_exemple():
    """
    Retourne des données d'exemple intégrées directement dans le code.

    Structure :
        ues        : liste de noms d'UE
        etudiants  : liste d'identifiants d'étudiants
        inscriptions : dict  {etudiant_id -> [ue1, ue2, ...]}

    Pour utiliser vos propres données, remplacez ce contenu ou
    utilisez charger_depuis_csv() ci-dessous.
    """
    ues = [
        "MATHS1", "ALGO",  "PROG",  "RESEAU",
        "BD",     "SYS",   "PHYS",  "ANGLAIS",
        "STAT",   "GRAPH",
    ]

    # inscriptions[etudiant] = liste des UE suivies
    inscriptions = {
        "E01": ["MATHS1", "ALGO",  "PROG",   "ANGLAIS"],
        "E02": ["MATHS1", "STAT",  "GRAPH",  "PHYS"],
        "E03": ["ALGO",   "BD",    "RESEAU", "SYS"],
        "E04": ["PROG",   "BD",    "ANGLAIS","GRAPH"],
        "E05": ["RESEAU", "SYS",   "PHYS",   "STAT"],
        "E06": ["MATHS1", "ALGO",  "BD",     "SYS"],
        "E07": ["PROG",   "RESEAU","GRAPH",  "STAT"],
        "E08": ["PHYS",   "ANGLAIS","MATHS1","ALGO"],
        "E09": ["SYS",    "BD",    "PROG",   "PHYS"],
        "E10": ["GRAPH",  "RESEAU","STAT",   "BD"],
        "E11": ["ANGLAIS","ALGO",  "GRAPH",  "SYS"],
        "E12": ["MATHS1", "PROG",  "STAT",   "RESEAU"],
    }

    etudiants = list(inscriptions.keys())
    return ues, etudiants, inscriptions


def charger_depuis_csv(chemin_ues: str, chemin_inscriptions: str):
    """
    Charge les données depuis deux fichiers CSV.

    Format attendu :
        ues.csv            → une colonne "code_ue"
        inscriptions.csv   → deux colonnes "etudiant_id", "code_ue"

    Exemple ues.csv :
        code_ue
        MATHS1
        ALGO
        ...

    Exemple inscriptions.csv :
        etudiant_id,code_ue
        E01,MATHS1
        E01,ALGO
        E02,MATHS1
        ...
    """
    ues = []
    with open(chemin_ues, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ues.append(row["code_ue"].strip())

    inscriptions = defaultdict(list)
    with open(chemin_inscriptions, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            etudiant = row["etudiant_id"].strip()
            ue       = row["code_ue"].strip()
            inscriptions[etudiant].append(ue)

    etudiants = list(inscriptions.keys())
    return ues, etudiants, dict(inscriptions)


# ─────────────────────────────────────────────────────────────────────────────
# 2.  CONSTRUCTION DU GRAPHE DE CONFLITS
# ─────────────────────────────────────────────────────────────────────────────

class GrapheConflits:
    """
    Représente le graphe de conflits entre UE.

    Un sommet = une UE.
    Une arête (u, v) = les UE u et v partagent au moins un étudiant
    → elles ne peuvent pas avoir lieu au même créneau.

    Deux représentations sont maintenues en parallèle :
        • self.matrice      : matrice d'adjacence  (liste de listes, n×n)
        • self.liste_adj    : liste d'adjacence    (dict {ue -> [voisins]})
    """

    def __init__(self, ues: list, inscriptions: dict):
        """
        Paramètres
        ----------
        ues          : liste ordonnée des noms d'UE
        inscriptions : dict {etudiant_id -> [ue1, ue2, ...]}
        """
        self.ues           = list(ues)          # sommets
        self.n             = len(self.ues)
        self.index         = {ue: i for i, ue in enumerate(self.ues)}
        self.inscriptions  = inscriptions

        # Structures initialisées vides
        self.matrice    = [[0] * self.n for _ in range(self.n)]
        self.liste_adj  = {ue: [] for ue in self.ues}

        # Construction effective
        self._construire()

    # ── Construction ─────────────────────────────────────────────────────────

    def _construire(self):
        """
        Parcourt les inscriptions pour détecter les conflits.

        Pour chaque étudiant, on prend toutes les paires d'UE qu'il suit :
        ce sont des arêtes du graphe de conflits.

        Complexité : O(E × k²) où E = nb étudiants, k = nb UE par étudiant
        """
        aretes_ajoutees = set()   # évite les doublons

        for etudiant, liste_ue in self.inscriptions.items():
            # Toutes les paires d'UE suivies par cet étudiant
            for i in range(len(liste_ue)):
                for j in range(i + 1, len(liste_ue)):
                    u = liste_ue[i]
                    v = liste_ue[j]

                    # Vérifier que les deux UE sont connues
                    if u not in self.index or v not in self.index:
                        continue

                    # Paire canonique (ordre alphabétique) pour éviter (u,v) et (v,u)
                    paire = (min(u, v), max(u, v))
                    if paire in aretes_ajoutees:
                        continue

                    aretes_ajoutees.add(paire)
                    self._ajouter_arete(u, v)

    def _ajouter_arete(self, u: str, v: str):
        """Ajoute l'arête (u, v) dans la matrice ET la liste d'adjacence."""
        i, j = self.index[u], self.index[v]

        # Matrice d'adjacence (symétrique, sans boucle)
        self.matrice[i][j] = 1
        self.matrice[j][i] = 1

        # Liste d'adjacence (bidirectionnelle)
        self.liste_adj[u].append(v)
        self.liste_adj[v].append(u)

    # ── Accesseurs ───────────────────────────────────────────────────────────

    def sont_voisins(self, u: str, v: str) -> bool:
        """Retourne True si u et v partagent au moins un étudiant."""
        return self.matrice[self.index[u]][self.index[v]] == 1

    def voisins(self, u: str) -> list:
        """Retourne la liste des UE en conflit avec u."""
        return list(self.liste_adj[u])

    # ── Descripteurs ─────────────────────────────────────────────────────────

    def nb_sommets(self) -> int:
        """Nombre d'UE (sommets du graphe)."""
        return self.n

    def nb_aretes(self) -> int:
        """
        Nombre d'arêtes du graphe.
        On compte les 1 dans le triangle supérieur de la matrice.
        """
        total = 0
        for i in range(self.n):
            for j in range(i + 1, self.n):
                if self.matrice[i][j] == 1:
                    total += 1
        return total

    def degres(self) -> dict:
        """
        Retourne un dict {ue -> degré}.
        Le degré d'un sommet = nombre de ses voisins = nombre d'UE en conflit avec lui.
        """
        return {ue: len(voisins) for ue, voisins in self.liste_adj.items()}

    def degre_max(self) -> int:
        """Degré maximum dans le graphe."""
        return max(self.degres().values(), default=0)

    def degre_moyen(self) -> float:
        """Degré moyen (= 2 × nb_aretes / nb_sommets)."""
        if self.n == 0:
            return 0.0
        return round(2 * self.nb_aretes() / self.n, 2)

    def densite(self) -> float:
        """
        Densité du graphe = nb_aretes / nb_aretes_possible.
        Un graphe complet a une densité de 1.
        """
        max_aretes = self.n * (self.n - 1) / 2
        if max_aretes == 0:
            return 0.0
        return round(self.nb_aretes() / max_aretes, 4)

    # ── Affichage ─────────────────────────────────────────────────────────────

    def afficher_matrice(self):
        """Affiche la matrice d'adjacence dans la console."""
        print("\n" + "=" * 60)
        print("MATRICE D'ADJACENCE")
        print("=" * 60)
        # En-tête
        largeur = max(len(ue) for ue in self.ues) + 1
        header  = " " * (largeur + 2) + "  ".join(f"{ue:>{largeur}}" for ue in self.ues)
        print(header)
        print("-" * len(header))
        for i, ue in enumerate(self.ues):
            ligne = f"{ue:>{largeur}} | " + "  ".join(
                f"{'1' if self.matrice[i][j] else '·':>{largeur}}"
                for j in range(self.n)
            )
            print(ligne)

    def afficher_liste_adjacence(self):
        """Affiche la liste d'adjacence dans la console."""
        print("\n" + "=" * 60)
        print("LISTE D'ADJACENCE")
        print("=" * 60)
        for ue in self.ues:
            voisins = sorted(self.liste_adj[ue])
            print(f"  {ue:<10} → {', '.join(voisins) if voisins else '(aucun voisin)'}")

    def afficher_descripteurs(self):
        """Affiche les statistiques du graphe dans la console."""
        degres = self.degres()
        print("\n" + "=" * 60)
        print("DESCRIPTEURS DU GRAPHE")
        print("=" * 60)
        print(f"  Nombre de sommets (UE)  : {self.nb_sommets()}")
        print(f"  Nombre d'arêtes         : {self.nb_aretes()}")
        print(f"  Degré maximum           : {self.degre_max()}")
        print(f"  Degré moyen             : {self.degre_moyen()}")
        print(f"  Densité                 : {self.densite()}")
        print()
        print(f"  {'UE':<12} {'Degré':>6}  {'Voisins'}")
        print(f"  {'-'*12} {'-'*6}  {'-'*30}")
        for ue in sorted(degres, key=lambda u: degres[u], reverse=True):
            voisins = sorted(self.liste_adj[ue])
            print(f"  {ue:<12} {degres[ue]:>6}  {', '.join(voisins)}")


# ─────────────────────────────────────────────────────────────────────────────
# 3.  VISUALISATION
# ─────────────────────────────────────────────────────────────────────────────

def visualiser_graphe(
    graphe: GrapheConflits,
    chemin_sortie: str = "graphe_conflits.png",
    coloration: dict = None,
    titre: str = "Graphe de Conflits entre UE",
):
    """
    Génère et sauvegarde une image PNG du graphe de conflits.

    Paramètres
    ----------
    graphe        : instance de GrapheConflits
    chemin_sortie : chemin du fichier PNG à créer
    coloration    : dict optionnel {ue -> numéro_créneau}
                    Si fourni, les nœuds sont colorés par créneau.
    titre         : titre de la figure
    """

    # ── Construction du graphe networkx ──────────────────────────────────────
    G = nx.Graph()
    G.add_nodes_from(graphe.ues)

    for u in graphe.ues:
        for v in graphe.liste_adj[u]:
            if u < v:      # chaque arête une seule fois
                G.add_edge(u, v)

    # ── Mise en page (layout) ─────────────────────────────────────────────────
    # spring_layout donne un rendu lisible pour des graphes de taille moyenne
    seed = 42          # reproductibilité
    if graphe.n <= 15:
        pos = nx.spring_layout(G, seed=seed, k=2.5)
    else:
        pos = nx.kamada_kawai_layout(G)

    # ── Couleurs des nœuds ────────────────────────────────────────────────────
    palette = [
        "#4E79A7", "#F28E2B", "#E15759", "#76B7B2", "#59A14F",
        "#EDC948", "#B07AA1", "#FF9DA7", "#9C755F", "#BAB0AC",
        "#D37295", "#A0CBE8", "#FFBE7D", "#8CD17D", "#86BCB6",
    ]

    if coloration:
        # Couleur selon le créneau attribué
        nb_couleurs = max(coloration.values()) + 1
        node_colors = [
            palette[coloration[ue] % len(palette)]
            for ue in graphe.ues
        ]
    else:
        # Couleur selon le degré (dégradé bleu → rouge)
        degres     = graphe.degres()
        deg_max    = graphe.degre_max() or 1
        cmap       = plt.cm.get_cmap("RdYlBu_r")
        node_colors = [cmap(degres[ue] / deg_max) for ue in graphe.ues]

    # ── Taille des nœuds proportionnelle au degré ─────────────────────────────
    degres     = graphe.degres()
    deg_max    = graphe.degre_max() or 1
    node_sizes = [
        800 + 1200 * (degres[ue] / deg_max)
        for ue in graphe.ues
    ]

    # ── Dessin ────────────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(14, 10))
    fig.patch.set_facecolor("#F8F9FA")
    ax.set_facecolor("#F8F9FA")

    # Arêtes
    nx.draw_networkx_edges(
        G, pos, ax=ax,
        edge_color="#AAAAAA",
        width=1.4,
        alpha=0.7,
    )

    # Nœuds
    nx.draw_networkx_nodes(
        G, pos, ax=ax,
        node_color=node_colors,
        node_size=node_sizes,
        alpha=0.92,
        linewidths=1.5,
        edgecolors="#333333",
    )

    # Étiquettes (noms des UE)
    nx.draw_networkx_labels(
        G, pos, ax=ax,
        font_size=9,
        font_weight="bold",
        font_color="#111111",
    )

    # ── Légende ───────────────────────────────────────────────────────────────
    if coloration:
        creneaux = sorted(set(coloration.values()))
        handles  = [
            mpatches.Patch(
                color=palette[c % len(palette)],
                label=f"Créneau {c + 1}"
            )
            for c in creneaux
        ]
        ax.legend(
            handles=handles,
            title="Créneaux attribués",
            loc="upper left",
            fontsize=9,
            framealpha=0.9,
        )

    # ── Infos textuelles ──────────────────────────────────────────────────────
    info = (
        f"Sommets : {graphe.nb_sommets()}   "
        f"Arêtes : {graphe.nb_aretes()}   "
        f"Degré max : {graphe.degre_max()}   "
        f"Densité : {graphe.densite()}"
    )
    ax.set_title(titre, fontsize=14, fontweight="bold", pad=16)
    fig.text(0.5, 0.02, info, ha="center", fontsize=9, color="#555555")

    ax.axis("off")
    plt.tight_layout(rect=[0, 0.04, 1, 1])

    # ── Sauvegarde ────────────────────────────────────────────────────────────
    plt.savefig(chemin_sortie, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\n  → Image sauvegardée : {chemin_sortie}")


def visualiser_matrice_adjacence(
    graphe: GrapheConflits,
    chemin_sortie: str = "matrice_adjacence.png",
):
    """
    Génère une visualisation heatmap de la matrice d'adjacence.
    Utile pour les rapports et les slides de présentation.
    """
    import numpy as np

    mat  = np.array(graphe.matrice, dtype=float)
    n    = graphe.n
    ues  = graphe.ues

    fig, ax = plt.subplots(figsize=(max(8, n * 0.7), max(7, n * 0.65)))
    fig.patch.set_facecolor("#F8F9FA")

    im = ax.imshow(mat, cmap="Blues", vmin=0, vmax=1)

    # Quadrillage
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(ues, rotation=45, ha="right", fontsize=9)
    ax.set_yticklabels(ues, fontsize=9)

    # Valeurs dans les cellules
    for i in range(n):
        for j in range(n):
            val   = int(mat[i, j])
            color = "white" if val == 1 else "#AAAAAA"
            ax.text(j, i, str(val), ha="center", va="center",
                    fontsize=8, color=color, fontweight="bold")

    ax.set_title("Matrice d'Adjacence — Graphe de Conflits",
                 fontsize=13, fontweight="bold", pad=14)
    plt.tight_layout()
    plt.savefig(chemin_sortie, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  → Matrice sauvegardée : {chemin_sortie}")


# ─────────────────────────────────────────────────────────────────────────────
# 4.  EXPORT CSV DES STRUCTURES
# ─────────────────────────────────────────────────────────────────────────────

def exporter_aretes_csv(graphe: GrapheConflits, chemin: str = "aretes_graphe.csv"):
    """
    Exporte la liste des arêtes dans un fichier CSV.
    Format : UE_A, UE_B
    """
    with open(chemin, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["UE_A", "UE_B"])
        for u in graphe.ues:
            for v in graphe.liste_adj[u]:
                if u < v:
                    writer.writerow([u, v])
    print(f"  → Arêtes exportées    : {chemin}")


def exporter_degres_csv(graphe: GrapheConflits, chemin: str = "degres_graphe.csv"):
    """
    Exporte les degrés de chaque UE dans un fichier CSV.
    Format : UE, Degré, Voisins
    """
    degres = graphe.degres()
    with open(chemin, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["UE", "Degre", "Voisins"])
        for ue in sorted(degres, key=lambda u: degres[u], reverse=True):
            voisins = ", ".join(sorted(graphe.liste_adj[ue]))
            writer.writerow([ue, degres[ue], voisins])
    print(f"  → Degrés exportés     : {chemin}")


# ─────────────────────────────────────────────────────────────────────────────
# 5.  PROGRAMME PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  GROUPE A — Structure du Graphe & Visualisation")
    print("  Projet : Planification d'Examens par Coloration")
    print("=" * 60)

    # ── Chargement des données ────────────────────────────────────────────────
    print("\n[1] Chargement des données...")

    # Décommentez la ligne ci-dessous pour utiliser vos propres fichiers CSV :
    # ues, etudiants, inscriptions = charger_depuis_csv("ues.csv", "inscriptions.csv")

    ues, etudiants, inscriptions = charger_donnees_exemple()

    print(f"    → {len(ues)} UE chargées      : {', '.join(ues)}")
    print(f"    → {len(etudiants)} étudiants chargés")

    # ── Construction du graphe ────────────────────────────────────────────────
    print("\n[2] Construction du graphe de conflits...")
    t0 = time.perf_counter()
    graphe = GrapheConflits(ues, inscriptions)
    duree  = (time.perf_counter() - t0) * 1000
    print(f"    → Graphe construit en {duree:.2f} ms")

    # ── Affichage des structures ──────────────────────────────────────────────
    print("\n[3] Affichage des structures de données...")
    graphe.afficher_liste_adjacence()
    graphe.afficher_matrice()

    # ── Descripteurs ─────────────────────────────────────────────────────────
    print("\n[4] Calcul des descripteurs...")
    graphe.afficher_descripteurs()

    # ── Visualisations ────────────────────────────────────────────────────────
    print("\n[5] Génération des visualisations...")
    visualiser_graphe(
        graphe,
        chemin_sortie="graphe_conflits.png",
        titre="Graphe de Conflits entre UE (couleur = degré)",
    )
    visualiser_matrice_adjacence(
        graphe,
        chemin_sortie="matrice_adjacence.png",
    )

    # ── Exports CSV ──────────────────────────────────────────────────────────
    print("\n[6] Export CSV...")
    exporter_aretes_csv(graphe,  "aretes_graphe.csv")
    exporter_degres_csv(graphe, "degres_graphe.csv")

    # ── Résumé final ──────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  RÉSUMÉ")
    print("=" * 60)
    print(f"  Sommets (UE)    : {graphe.nb_sommets()}")
    print(f"  Arêtes          : {graphe.nb_aretes()}")
    print(f"  Degré maximum   : {graphe.degre_max()}")
    print(f"  Degré moyen     : {graphe.degre_moyen()}")
    print(f"  Densité         : {graphe.densite()}")
    print()
    print("  Fichiers générés :")
    print("    graphe_conflits.png   — visualisation du graphe")
    print("    matrice_adjacence.png — heatmap de la matrice")
    print("    aretes_graphe.csv     — liste des arêtes")
    print("    degres_graphe.csv     — degrés par UE")
    print("=" * 60)

    return graphe   # retourné pour que les autres groupes puissent l'importer


# Point d'entrée
if __name__ == "__main__":
    main()
