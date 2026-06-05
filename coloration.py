"""
=============================================================================
 coloration.py — Groupe B : Le Moteur de Coloration
 Projet : Planification d'Examens par Coloration de Graphes
 Niveau : L2 Informatique — Théorie des Graphes
=============================================================================

Ce fichier implémente :
  1. Algorithme Welsh-Powell
       → Tri des sommets par degré décroissant, puis coloration gloutonne
  2. Algorithme DSATUR
       → Choix dynamique du sommet le plus saturé à chaque étape
  3. Benchmark comparatif
       → Temps d'exécution, nombre chromatique, tableau de résultats
  4. Visualisation des résultats (graphes colorés + histogrammes)

=============================================================================
"""

import time
import csv
import copy
import random
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# Import du Groupe A
from graphe import GrapheConflits, charger_donnees_exemple


# ─────────────────────────────────────────────────────────────────────────────
# UTILITAIRES COMMUNS
# ─────────────────────────────────────────────────────────────────────────────

def couleurs_utilisees_par_voisins(graphe: GrapheConflits,
                                    ue: str,
                                    coloration: dict) -> set:
    """
    Retourne l'ensemble des couleurs (créneaux) déjà attribuées
    aux voisins d'une UE donnée.

    Paramètres
    ----------
    graphe     : le graphe de conflits
    ue         : l'UE dont on examine le voisinage
    coloration : dict {ue -> numéro_créneau} (coloration partielle en cours)
    """
    couleurs = set()
    for voisin in graphe.voisins(ue):
        if voisin in coloration:
            couleurs.add(coloration[voisin])
    return couleurs


def plus_petite_couleur_disponible(couleurs_interdites: set) -> int:
    """
    Retourne le plus petit entier >= 0 absent de couleurs_interdites.
    C'est le créneau le moins coûteux que l'on peut attribuer.

    Exemple : {0, 1, 3} → retourne 2
    """
    couleur = 0
    while couleur in couleurs_interdites:
        couleur += 1
    return couleur


def est_coloration_valide(graphe: GrapheConflits, coloration: dict) -> bool:
    """
    Vérifie qu'aucune paire de voisins ne partage la même couleur.
    Utilisé pour valider les résultats des deux algorithmes.

    Retourne True si la coloration est valide, False sinon.
    """
    for ue in graphe.ues:
        for voisin in graphe.voisins(ue):
            if ue in coloration and voisin in coloration:
                if coloration[ue] == coloration[voisin]:
                    return False
    return True


# ─────────────────────────────────────────────────────────────────────────────
# 1.  ALGORITHME WELSH-POWELL
# ─────────────────────────────────────────────────────────────────────────────

def welsh_powell(graphe: GrapheConflits) -> dict:
    """
    Algorithme de Welsh-Powell — coloration gloutonne par degré décroissant.

    Principe
    --------
    1. Trier tous les sommets par degré décroissant.
       → On commence par les UE les plus "conflictuelles".
    2. Parcourir la liste triée dans l'ordre.
    3. Pour chaque UE non encore colorée, lui attribuer le plus petit
       créneau qui n'est pas utilisé par l'un de ses voisins.

    Complexité : O(n² + m) où n = nb sommets, m = nb arêtes.

    Retourne
    --------
    dict {ue -> numéro_créneau}   (les créneaux commencent à 0)
    """
    # Étape 1 : tri par degré décroissant
    # En cas d'égalité de degré, on trie par nom (ordre alphabétique)
    # pour assurer un résultat déterministe.
    degres = graphe.degres()
    ordre  = sorted(graphe.ues,
                    key=lambda u: (-degres[u], u))

    coloration = {}

    # Étape 2 : coloration gloutonne dans l'ordre trié
    for ue in ordre:
        interdites = couleurs_utilisees_par_voisins(graphe, ue, coloration)
        coloration[ue] = plus_petite_couleur_disponible(interdites)

    return coloration


# ─────────────────────────────────────────────────────────────────────────────
# 2.  ALGORITHME DSATUR
# ─────────────────────────────────────────────────────────────────────────────

def dsatur(graphe: GrapheConflits) -> dict:
    """
    Algorithme DSATUR (Degree of SATURation) — Brélaz, 1979.

    Principe
    --------
    À chaque étape, on choisit le sommet non coloré dont le degré
    de saturation est le plus élevé.

    Degré de saturation d'un sommet u =
        nombre de couleurs DISTINCTES utilisées dans le voisinage de u.

    En cas d'égalité de saturation → on prend celui de degré (dans le
    graphe original) le plus élevé.  Nouvelle égalité → ordre alphabétique.

    Cet algorithme est généralement plus performant que Welsh-Powell
    car il s'adapte dynamiquement à la coloration en cours.

    Complexité : O(n² + m)

    Retourne
    --------
    dict {ue -> numéro_créneau}
    """
    coloration  = {}                          # {ue -> créneau}
    saturation  = {ue: 0 for ue in graphe.ues}   # degré de saturation
    degres      = graphe.degres()
    non_colores = set(graphe.ues)

    while non_colores:
        # Choisir le sommet non coloré avec la saturation maximale
        # (égalité → degré max → ordre alphabétique)
        u = max(
            non_colores,
            key=lambda x: (saturation[x], degres[x], x)
        )

        # Attribuer le plus petit créneau disponible
        interdites     = couleurs_utilisees_par_voisins(graphe, u, coloration)
        coloration[u]  = plus_petite_couleur_disponible(interdites)
        non_colores.remove(u)

        # Mettre à jour la saturation des voisins non colorés
        for voisin in graphe.voisins(u):
            if voisin in non_colores:
                # Recompute : nb de couleurs distinctes dans son voisinage
                saturation[voisin] = len(
                    couleurs_utilisees_par_voisins(graphe, voisin, coloration)
                )

    return coloration


# ─────────────────────────────────────────────────────────────────────────────
# 3.  RÉSULTAT STRUCTURÉ
# ─────────────────────────────────────────────────────────────────────────────

class ResultatColoration:
    """
    Encapsule le résultat d'un algorithme de coloration.

    Attributs
    ---------
    algorithme    : nom de l'algorithme ("Welsh-Powell" ou "DSATUR")
    coloration    : dict {ue -> créneau}
    nb_couleurs   : nombre chromatique obtenu (= nb créneaux utilisés)
    temps_ms      : temps d'exécution en millisecondes
    valide        : True si aucune contrainte n'est violée
    creneaux      : dict {créneau -> [liste d'UE]}
    """

    def __init__(self, algorithme: str, coloration: dict,
                 temps_ms: float, graphe: GrapheConflits):
        self.algorithme  = algorithme
        self.coloration  = coloration
        self.temps_ms    = round(temps_ms, 4)
        self.nb_couleurs = max(coloration.values()) + 1 if coloration else 0
        self.valide      = est_coloration_valide(graphe, coloration)

        # Regroupement UE par créneau
        self.creneaux: dict[int, list] = {}
        for ue, creneau in coloration.items():
            self.creneaux.setdefault(creneau, []).append(ue)

    def afficher(self):
        """Affiche le résultat détaillé dans la console."""
        statut = "✓ VALIDE" if self.valide else "✗ INVALIDE"
        print(f"\n{'─'*60}")
        print(f"  Algorithme    : {self.algorithme}  [{statut}]")
        print(f"  Créneaux      : {self.nb_couleurs}")
        print(f"  Temps         : {self.temps_ms} ms")
        print(f"{'─'*60}")
        for creneau in sorted(self.creneaux):
            ues = ", ".join(sorted(self.creneaux[creneau]))
            print(f"  Créneau {creneau + 1:>2}  → {ues}")

    def vers_csv(self, chemin: str):
        """Exporte la coloration dans un fichier CSV."""
        with open(chemin, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["UE", "Creneau", "Algorithme"])
            for ue in sorted(self.coloration):
                writer.writerow([ue, self.coloration[ue] + 1, self.algorithme])
        print(f"  → Coloration exportée : {chemin}")


# ─────────────────────────────────────────────────────────────────────────────
# 4.  BENCHMARK
# ─────────────────────────────────────────────────────────────────────────────

def executer_algorithme(nom: str, algo_fn, graphe: GrapheConflits,
                         nb_repetitions: int = 100) -> ResultatColoration:
    """
    Exécute un algorithme de coloration et mesure son temps moyen
    sur nb_repetitions répétitions (pour plus de précision).

    Retourne un ResultatColoration.
    """
    # Première exécution pour obtenir la coloration
    coloration = algo_fn(graphe)

    # Mesure du temps sur nb_repetitions exécutions
    debut = time.perf_counter()
    for _ in range(nb_repetitions):
        algo_fn(graphe)
    fin    = time.perf_counter()
    temps_ms = ((fin - debut) / nb_repetitions) * 1000

    return ResultatColoration(nom, coloration, temps_ms, graphe)


def benchmark(graphe: GrapheConflits,
              nb_repetitions: int = 100) -> tuple:
    """
    Lance les deux algorithmes sur le même graphe et compare les résultats.

    Retourne
    --------
    (ResultatColoration_WP, ResultatColoration_DSATUR)
    """
    print("\n" + "=" * 60)
    print("  BENCHMARK — Comparaison Welsh-Powell vs DSATUR")
    print(f"  (moyenne sur {nb_repetitions} répétitions)")
    print("=" * 60)

    res_wp = executer_algorithme(
        "Welsh-Powell", welsh_powell, graphe, nb_repetitions
    )
    res_ds = executer_algorithme(
        "DSATUR", dsatur, graphe, nb_repetitions
    )

    # Affichage des résultats individuels
    res_wp.afficher()
    res_ds.afficher()

    # Tableau comparatif
    print("\n" + "=" * 60)
    print("  TABLEAU COMPARATIF")
    print("=" * 60)
    print(f"  {'Critère':<28} {'Welsh-Powell':>14} {'DSATUR':>14}")
    print(f"  {'─'*28} {'─'*14} {'─'*14}")
    print(f"  {'Créneaux utilisés':<28} {res_wp.nb_couleurs:>14} {res_ds.nb_couleurs:>14}")
    print(f"  {'Temps moyen (ms)':<28} {res_wp.temps_ms:>14.4f} {res_ds.temps_ms:>14.4f}")
    print(f"  {'Coloration valide':<28} {'Oui' if res_wp.valide else 'Non':>14} {'Oui' if res_ds.valide else 'Non':>14}")

    # Conclusion
    print("\n  CONCLUSION :")
    if res_wp.nb_couleurs < res_ds.nb_couleurs:
        print(f"  → Welsh-Powell utilise moins de créneaux ({res_wp.nb_couleurs} vs {res_ds.nb_couleurs})")
    elif res_ds.nb_couleurs < res_wp.nb_couleurs:
        print(f"  → DSATUR utilise moins de créneaux ({res_ds.nb_couleurs} vs {res_wp.nb_couleurs})")
    else:
        print(f"  → Les deux algorithmes donnent le même nombre de créneaux ({res_wp.nb_couleurs})")

    if res_wp.temps_ms < res_ds.temps_ms:
        print(f"  → Welsh-Powell est plus rapide ({res_wp.temps_ms:.4f} ms vs {res_ds.temps_ms:.4f} ms)")
    else:
        print(f"  → DSATUR est plus rapide ({res_ds.temps_ms:.4f} ms vs {res_wp.temps_ms:.4f} ms)")

    return res_wp, res_ds


def benchmark_multi_graphes(tailles: list = None) -> list:
    """
    Benchmark sur plusieurs graphes aléatoires de tailles croissantes.
    Permet d'observer la scalabilité des deux algorithmes.

    Paramètres
    ----------
    tailles : liste du nombre d'UE par graphe (ex: [5, 10, 20, 50])

    Retourne
    --------
    liste de dicts avec les métriques pour chaque taille
    """
    if tailles is None:
        tailles = [5, 10, 15, 20, 30, 50]

    print("\n" + "=" * 60)
    print("  BENCHMARK MULTI-GRAPHES (scalabilité)")
    print("=" * 60)
    print(f"  {'UE':>5} {'Arêtes':>7} {'WP créneaux':>12} {'WP ms':>10} "
          f"{'DS créneaux':>12} {'DS ms':>10}")
    print(f"  {'─'*5} {'─'*7} {'─'*12} {'─'*10} {'─'*12} {'─'*10}")

    resultats = []

    for n in tailles:
        # Génération d'un graphe aléatoire de n UE
        ues_test = [f"UE{i:02d}" for i in range(n)]
        inscriptions_test = {}
        nb_etudiants = n * 3
        for e in range(nb_etudiants):
            nb_ue_par_etu = random.randint(2, min(5, n))
            inscriptions_test[f"E{e:03d}"] = random.sample(ues_test, nb_ue_par_etu)

        g = GrapheConflits(ues_test, inscriptions_test)

        res_wp = executer_algorithme("Welsh-Powell", welsh_powell, g, nb_repetitions=50)
        res_ds = executer_algorithme("DSATUR",       dsatur,       g, nb_repetitions=50)

        print(f"  {n:>5} {g.nb_aretes():>7} {res_wp.nb_couleurs:>12} "
              f"{res_wp.temps_ms:>10.4f} {res_ds.nb_couleurs:>12} {res_ds.temps_ms:>10.4f}")

        resultats.append({
            "n": n,
            "aretes": g.nb_aretes(),
            "wp_creneaux": res_wp.nb_couleurs,
            "wp_ms": res_wp.temps_ms,
            "ds_creneaux": res_ds.nb_couleurs,
            "ds_ms": res_ds.temps_ms,
        })

    return resultats


# ─────────────────────────────────────────────────────────────────────────────
# 5.  VISUALISATION DES RÉSULTATS
# ─────────────────────────────────────────────────────────────────────────────

PALETTE = [
    "#4E79A7", "#F28E2B", "#E15759", "#76B7B2", "#59A14F",
    "#EDC948", "#B07AA1", "#FF9DA7", "#9C755F", "#BAB0AC",
    "#D37295", "#A0CBE8", "#FFBE7D", "#8CD17D", "#86BCB6",
]


def visualiser_coloration(graphe: GrapheConflits,
                           resultat: ResultatColoration,
                           chemin_sortie: str = None):
    """
    Génère un graphe coloré par créneau (une couleur = un créneau).
    Réutilise la fonction du Groupe A si disponible, sinon matplotlib direct.
    """
    try:
        from graphe import visualiser_graphe
        if chemin_sortie is None:
            nom = resultat.algorithme.lower().replace("-", "_").replace(" ", "_")
            chemin_sortie = f"graphe_{nom}.png"
        visualiser_graphe(
            graphe,
            chemin_sortie=chemin_sortie,
            coloration=resultat.coloration,
            titre=f"Coloration {resultat.algorithme} — {resultat.nb_couleurs} créneaux",
        )
    except Exception as e:
        print(f"  ✗ Visualisation impossible : {e}")


def visualiser_benchmark_comparatif(res_wp: ResultatColoration,
                                     res_ds: ResultatColoration,
                                     chemin_sortie: str = "benchmark_comparaison.png"):
    """
    Génère un graphique à barres comparant :
      - le nombre de créneaux utilisés
      - le temps d'exécution
    pour les deux algorithmes.
    """
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.patch.set_facecolor("#F8F9FA")
    fig.suptitle("Benchmark : Welsh-Powell vs DSATUR",
                 fontsize=14, fontweight="bold", y=1.02)

    algos   = ["Welsh-Powell", "DSATUR"]
    couleur = ["#4E79A7", "#F28E2B"]

    # ── Graphique 1 : nombre de créneaux ──────────────────────────────────
    ax1 = axes[0]
    ax1.set_facecolor("#F8F9FA")
    valeurs = [res_wp.nb_couleurs, res_ds.nb_couleurs]
    barres  = ax1.bar(algos, valeurs, color=couleur, width=0.5,
                      edgecolor="#333333", linewidth=0.8)
    ax1.set_title("Nombre de créneaux utilisés", fontweight="bold")
    ax1.set_ylabel("Créneaux")
    ax1.set_ylim(0, max(valeurs) * 1.35)
    for barre, val in zip(barres, valeurs):
        ax1.text(barre.get_x() + barre.get_width() / 2,
                 barre.get_height() + 0.05,
                 str(val), ha="center", va="bottom",
                 fontweight="bold", fontsize=13)
    ax1.spines[["top", "right"]].set_visible(False)

    # ── Graphique 2 : temps d'exécution ───────────────────────────────────
    ax2 = axes[1]
    ax2.set_facecolor("#F8F9FA")
    valeurs2 = [res_wp.temps_ms, res_ds.temps_ms]
    barres2  = ax2.bar(algos, valeurs2, color=couleur, width=0.5,
                       edgecolor="#333333", linewidth=0.8)
    ax2.set_title("Temps d'exécution moyen", fontweight="bold")
    ax2.set_ylabel("Temps (ms)")
    ax2.set_ylim(0, max(valeurs2) * 1.4)
    for barre, val in zip(barres2, valeurs2):
        ax2.text(barre.get_x() + barre.get_width() / 2,
                 barre.get_height() + max(valeurs2) * 0.01,
                 f"{val:.4f} ms", ha="center", va="bottom",
                 fontweight="bold", fontsize=10)
    ax2.spines[["top", "right"]].set_visible(False)

    plt.tight_layout()
    plt.savefig(chemin_sortie, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  → Benchmark sauvegardé : {chemin_sortie}")


def visualiser_scalabilite(resultats: list,
                            chemin_sortie: str = "benchmark_scalabilite.png"):
    """
    Courbes de scalabilité (nb UE → nb créneaux et temps d'exécution).
    """
    ns          = [r["n"]           for r in resultats]
    wp_creneaux = [r["wp_creneaux"] for r in resultats]
    ds_creneaux = [r["ds_creneaux"] for r in resultats]
    wp_ms       = [r["wp_ms"]       for r in resultats]
    ds_ms       = [r["ds_ms"]       for r in resultats]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    fig.patch.set_facecolor("#F8F9FA")
    fig.suptitle("Scalabilité : Welsh-Powell vs DSATUR",
                 fontsize=14, fontweight="bold")

    # ── Nombre de créneaux ────────────────────────────────────────────────
    ax1.set_facecolor("#F8F9FA")
    ax1.plot(ns, wp_creneaux, "o-", color="#4E79A7",
             linewidth=2, markersize=6, label="Welsh-Powell")
    ax1.plot(ns, ds_creneaux, "s-", color="#F28E2B",
             linewidth=2, markersize=6, label="DSATUR")
    ax1.set_xlabel("Nombre d'UE (sommets)")
    ax1.set_ylabel("Créneaux utilisés")
    ax1.set_title("Nombre de créneaux selon la taille", fontweight="bold")
    ax1.legend()
    ax1.spines[["top", "right"]].set_visible(False)

    # ── Temps d'exécution ─────────────────────────────────────────────────
    ax2.set_facecolor("#F8F9FA")
    ax2.plot(ns, wp_ms, "o-", color="#4E79A7",
             linewidth=2, markersize=6, label="Welsh-Powell")
    ax2.plot(ns, ds_ms, "s-", color="#F28E2B",
             linewidth=2, markersize=6, label="DSATUR")
    ax2.set_xlabel("Nombre d'UE (sommets)")
    ax2.set_ylabel("Temps moyen (ms)")
    ax2.set_title("Temps d'exécution selon la taille", fontweight="bold")
    ax2.legend()
    ax2.spines[["top", "right"]].set_visible(False)

    plt.tight_layout()
    plt.savefig(chemin_sortie, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  → Scalabilité sauvegardée : {chemin_sortie}")


def visualiser_repartition_creneaux(res_wp: ResultatColoration,
                                     res_ds: ResultatColoration,
                                     chemin_sortie: str = "repartition_creneaux.png"):
    """
    Diagramme en barres empilées montrant quelles UE sont dans quel créneau,
    pour chaque algorithme.
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.patch.set_facecolor("#F8F9FA")
    fig.suptitle("Répartition des UE par créneau",
                 fontsize=14, fontweight="bold")

    for ax, res in zip(axes, [res_wp, res_ds]):
        ax.set_facecolor("#F8F9FA")
        creneaux = sorted(res.creneaux.keys())
        y_pos    = range(len(creneaux))

        for i, creneau in enumerate(creneaux):
            ues    = sorted(res.creneaux[creneau])
            nb_ues = len(ues)
            couleur = PALETTE[creneau % len(PALETTE)]
            ax.barh(i, nb_ues, color=couleur,
                    edgecolor="#333333", linewidth=0.6, height=0.6)
            label = ", ".join(ues)
            ax.text(nb_ues + 0.05, i, label,
                    va="center", fontsize=8, color="#333333")

        ax.set_yticks(list(y_pos))
        ax.set_yticklabels([f"Créneau {c+1}" for c in creneaux])
        ax.set_xlabel("Nombre d'UE")
        ax.set_title(f"{res.algorithme} — {res.nb_couleurs} créneaux",
                     fontweight="bold")
        ax.set_xlim(0, max(len(v) for v in res.creneaux.values()) * 2.2)
        ax.spines[["top", "right"]].set_visible(False)

    plt.tight_layout()
    plt.savefig(chemin_sortie, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  → Répartition sauvegardée : {chemin_sortie}")


# ─────────────────────────────────────────────────────────────────────────────
# 6.  PROGRAMME PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  GROUPE B — Le Moteur de Coloration")
    print("  Projet : Planification d'Examens par Coloration")
    print("=" * 60)

    # ── Chargement du graphe (Groupe A) ───────────────────────────────────
    print("\n[1] Construction du graphe de conflits...")
    ues, etudiants, inscriptions = charger_donnees_exemple()
    graphe = GrapheConflits(ues, inscriptions)
    print(f"    → {graphe.nb_sommets()} sommets, {graphe.nb_aretes()} arêtes")

    # ── Benchmark principal ───────────────────────────────────────────────
    print("\n[2] Exécution et benchmark des algorithmes...")
    res_wp, res_ds = benchmark(graphe, nb_repetitions=200)

    # ── Export CSV ────────────────────────────────────────────────────────
    print("\n[3] Export CSV des colorations...")
    res_wp.vers_csv("coloration_welsh_powell.csv")
    res_ds.vers_csv("coloration_dsatur.csv")

    # ── Visualisations ────────────────────────────────────────────────────
    print("\n[4] Génération des visualisations...")
    visualiser_coloration(graphe, res_wp, "graphe_welsh_powell.png")
    visualiser_coloration(graphe, res_ds, "graphe_dsatur.png")
    visualiser_benchmark_comparatif(res_wp, res_ds, "benchmark_comparaison.png")
    visualiser_repartition_creneaux(res_wp, res_ds, "repartition_creneaux.png")

    # ── Benchmark multi-graphes ───────────────────────────────────────────
    print("\n[5] Benchmark de scalabilité...")
    random.seed(42)
    resultats_multi = benchmark_multi_graphes([5, 10, 15, 20, 30, 50])
    visualiser_scalabilite(resultats_multi, "benchmark_scalabilite.png")

    # ── Résumé final ──────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  RÉSUMÉ FINAL")
    print("=" * 60)
    print(f"  Welsh-Powell : {res_wp.nb_couleurs} créneaux en {res_wp.temps_ms:.4f} ms  "
          f"({'✓' if res_wp.valide else '✗'})")
    print(f"  DSATUR       : {res_ds.nb_couleurs} créneaux en {res_ds.temps_ms:.4f} ms  "
          f"({'✓' if res_ds.valide else '✗'})")
    print()
    print("  Fichiers générés :")
    print("    graphe_welsh_powell.png     — graphe coloré (WP)")
    print("    graphe_dsatur.png           — graphe coloré (DSATUR)")
    print("    benchmark_comparaison.png   — barres comparatives")
    print("    repartition_creneaux.png    — UE par créneau")
    print("    benchmark_scalabilite.png   — courbes de scalabilité")
    print("    coloration_welsh_powell.csv — coloration WP")
    print("    coloration_dsatur.csv       — coloration DSATUR")
    print("=" * 60)

    # Retourner le meilleur résultat pour le Groupe C
    # (préférer DSATUR s'il utilise moins de créneaux, sinon Welsh-Powell)
    meilleur = res_ds if res_ds.nb_couleurs <= res_wp.nb_couleurs else res_wp
    print(f"\n  Meilleure coloration retenue : {meilleur.algorithme}")
    return graphe, res_wp, res_ds, meilleur


if __name__ == "__main__":
    main()
