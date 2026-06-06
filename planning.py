"""
=============================================================================
 planning.py — Groupe C : Génération du Planning Final
 Projet : Planification d'Examens par Coloration de Graphes
 Niveau : L2 Informatique — Théorie des Graphes
=============================================================================

Ce fichier implémente :
  1. Génération du tableau planning (créneau × salle)
  2. Export CSV du planning au format requis (créneau × salle,
     avec code UE + effectif dans chaque cellule)
  3. Visualisation matplotlib du planning sous forme de grille colorée
  4. Rapport de synthèse final (console)

Dépendances : graphe.py, coloration.py, affectation.py

=============================================================================
"""

import csv
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch

from graphe      import GrapheConflits, charger_donnees_exemple
from coloration  import dsatur
from affectation import (MoteurAffectation, MoteurAudit,
                          salles_exemple, ues_info_exemple, Affectation)


# ─────────────────────────────────────────────────────────────────────────────
# 1.  CONSTRUCTION DU TABLEAU PLANNING
# ─────────────────────────────────────────────────────────────────────────────

def construire_tableau(affectations: list, salles: list,
                        ues_info: dict) -> dict:
    """
    Construit un tableau bidimensionnel créneau × salle.

    Retourne
    --------
    dict {(creneau, salle_code) -> dict}
        Chaque cellule contient :
            "ue_code"  : str  (code de l'UE, "" si vide)
            "effectif" : int  (0 si vide)
            "labo"     : bool (True si salle labo)
            "succes"   : bool (False si affectation échouée)
    """
    # Récupère tous les créneaux et codes de salles
    all_creneaux = sorted({a.creneau for a in affectations})
    all_salles   = sorted({s.code for s in salles})

    # Initialise toutes les cellules à vide
    tableau = {}
    for c in all_creneaux:
        for s in all_salles:
            salle_obj = next((x for x in salles if x.code == s), None)
            tableau[(c, s)] = {
                "ue_code"  : "",
                "effectif" : 0,
                "labo"     : salle_obj.est_labo if salle_obj else False,
                "succes"   : True,
            }

    # Remplit les cellules avec les affectations réussies
    for aff in affectations:
        if aff.succes and aff.salle:
            key = (aff.creneau, aff.salle.code)
            info = ues_info.get(aff.ue_code)
            tableau[key] = {
                "ue_code"  : aff.ue_code,
                "effectif" : info.effectif if info else 0,
                "labo"     : aff.salle.est_labo,
                "succes"   : True,
            }

    return tableau, all_creneaux, all_salles


# ─────────────────────────────────────────────────────────────────────────────
# 2.  AFFICHAGE CONSOLE DU PLANNING
# ─────────────────────────────────────────────────────────────────────────────

def afficher_planning_console(tableau: dict, creneaux: list, salles_codes: list,
                               ues_info: dict, salles: list):
    """Affiche le planning sous forme de tableau texte dans la console."""
    larg_salle   = max(len(s) for s in salles_codes) + 2
    larg_cellule = 14

    print("\n" + "=" * 60)
    print("  PLANNING FINAL  (créneau × salle)")
    print("=" * 60)

    # En-tête (noms des salles)
    header = f"  {'Créneau':<10}" + "".join(
        f"{s:^{larg_cellule}}" for s in salles_codes
    )
    print(header)
    print("  " + "─" * (10 + larg_cellule * len(salles_codes)))

    for c in creneaux:
        ligne = f"  Créneau {c:<2} "
        for s in salles_codes:
            cell = tableau.get((c, s), {})
            ue   = cell.get("ue_code", "")
            eff  = cell.get("effectif", 0)
            if ue:
                contenu = f"{ue}({eff})"
            else:
                salle_obj = next((x for x in salles if x.code == s), None)
                contenu   = "[LABO]" if (salle_obj and salle_obj.est_labo) else "·"
            ligne += f"{contenu:^{larg_cellule}}"
        print(ligne)

    print("  " + "─" * (10 + larg_cellule * len(salles_codes)))

    # UE non affectées
    print()
    ues_non_affectees = [
        aff for aff in []   # sera passé séparément si besoin
    ]


# ─────────────────────────────────────────────────────────────────────────────
# 3.  EXPORT CSV DU PLANNING
# ─────────────────────────────────────────────────────────────────────────────

def exporter_planning_csv(tableau: dict, creneaux: list, salles_codes: list,
                           ues_info: dict, salles: list,
                           chemin: str = "planning_final.csv"):
    """
    Exporte le planning au format CSV créneau × salle.

    Format de chaque cellule : "CODE_UE (effectif)"
    Les cellules vides restent vides.
    """
    with open(chemin, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # En-tête : "Créneau" + codes des salles
        entete = ["Créneau"] + salles_codes
        writer.writerow(entete)

        for c in creneaux:
            ligne = [f"Créneau {c}"]
            for s in salles_codes:
                cell = tableau.get((c, s), {})
                ue   = cell.get("ue_code", "")
                eff  = cell.get("effectif", 0)
                if ue:
                    ligne.append(f"{ue} ({eff} étudiants)")
                else:
                    salle_obj = next((x for x in salles if x.code == s), None)
                    ligne.append("[LABO LIBRE]" if (salle_obj and salle_obj.est_labo) else "")
            writer.writerow(ligne)

    print(f"  → Planning CSV exporté   : {chemin}")


def exporter_affectations_detaillees_csv(affectations: list, ues_info: dict,
                                          chemin: str = "affectations_detaillees.csv"):
    """
    Exporte une version détaillée ligne par ligne :
    UE, Créneau, Salle, Effectif, Type salle, Surveillant, Filière, Statut
    """
    with open(chemin, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Code UE", "Créneau", "Salle", "Type salle",
            "Effectif", "Capacité salle", "Taux occupation (%)",
            "Surveillant", "Filière", "Statut", "Remarque"
        ])
        for aff in sorted(affectations, key=lambda a: (a.creneau, a.ue_code)):
            info = ues_info.get(aff.ue_code)
            if aff.succes and aff.salle:
                taux = round(info.effectif / aff.salle.capacite * 100, 1) if info else 0
                writer.writerow([
                    aff.ue_code,
                    f"Créneau {aff.creneau}",
                    aff.salle.code,
                    "Labo" if aff.salle.est_labo else "Standard",
                    info.effectif if info else "",
                    aff.salle.capacite,
                    taux,
                    info.surveillant if info else "",
                    info.filiere if info else "",
                    "OK",
                    "",
                ])
            else:
                writer.writerow([
                    aff.ue_code,
                    f"Créneau {aff.creneau}",
                    "", "", "",
                    info.effectif if info else "",
                    "",
                    info.surveillant if info else "",
                    info.filiere if info else "",
                    "ÉCHEC",
                    aff.raison,
                ])

    print(f"  → Affectations détaillées : {chemin}")


# ─────────────────────────────────────────────────────────────────────────────
# 4.  VISUALISATION MATPLOTLIB DU PLANNING
# ─────────────────────────────────────────────────────────────────────────────

PALETTE_FILIERES = {
    "INFO"    : "#AED6F1",
    "RESEAU"  : "#A9DFBF",
    "SCIENCE" : "#F9E79F",
    "LANGUE"  : "#F5CBA7",
    "AUTRE"   : "#D7BDE2",
}
COULEUR_VIDE     = "#F2F3F4"
COULEUR_LABO     = "#EBF5FB"
COULEUR_ECHEC    = "#FADBD8"


def visualiser_planning(tableau: dict, creneaux: list, salles_codes: list,
                         ues_info: dict, salles: list,
                         affectations: list,
                         chemin_sortie: str = "planning_visualisation.png"):
    """
    Génère une image PNG du planning sous forme de grille colorée.

    Chaque cellule est colorée selon la filière de l'UE.
    Les cellules vides sont grises, les labos libres en bleu clair.
    """
    nb_creneaux = len(creneaux)
    nb_salles   = len(salles_codes)

    # Dimensions adaptatives
    larg_cel = 2.2
    haut_cel = 1.0
    fig_w    = max(12, nb_salles * larg_cel + 2.5)
    fig_h    = max(6,  nb_creneaux * haut_cel + 2.0)

    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    fig.patch.set_facecolor("#F8F9FA")
    ax.set_facecolor("#F8F9FA")
    ax.set_xlim(0, nb_salles)
    ax.set_ylim(0, nb_creneaux)
    ax.axis("off")

    # ── Dessin des cellules ───────────────────────────────────────────────
    for ci, c in enumerate(reversed(creneaux)):   # créneau 1 en haut
        y = ci
        for si, s in enumerate(salles_codes):
            x    = si
            cell = tableau.get((c, s), {})
            ue   = cell.get("ue_code", "")

            # Couleur de la cellule
            if ue:
                info   = ues_info.get(ue)
                filiere = info.filiere if info else "AUTRE"
                couleur = PALETTE_FILIERES.get(filiere, PALETTE_FILIERES["AUTRE"])
            elif cell.get("labo"):
                couleur = COULEUR_LABO
            else:
                couleur = COULEUR_VIDE

            # Rectangle
            rect = FancyBboxPatch(
                (x + 0.04, y + 0.05),
                0.92, 0.88,
                boxstyle="round,pad=0.02",
                facecolor=couleur,
                edgecolor="#BBBBBB",
                linewidth=0.8,
            )
            ax.add_patch(rect)

            # Texte dans la cellule
            if ue:
                info = ues_info.get(ue)
                eff  = info.effectif if info else 0
                surv = info.surveillant if info else ""
                ax.text(x + 0.5, y + 0.62, ue,
                        ha="center", va="center",
                        fontsize=8.5, fontweight="bold", color="#1A1A1A")
                ax.text(x + 0.5, y + 0.36, f"{eff} étud.",
                        ha="center", va="center",
                        fontsize=6.5, color="#444444")
                ax.text(x + 0.5, y + 0.16, surv,
                        ha="center", va="center",
                        fontsize=5.5, color="#888888", style="italic")
            elif cell.get("labo"):
                ax.text(x + 0.5, y + 0.48, "LABO\nlibre",
                        ha="center", va="center",
                        fontsize=6, color="#7FB3D3")
            else:
                ax.text(x + 0.5, y + 0.48, "—",
                        ha="center", va="center",
                        fontsize=10, color="#CCCCCC")

    # ── En-têtes colonnes (salles) ────────────────────────────────────────
    for si, s in enumerate(salles_codes):
        salle_obj = next((x for x in salles if x.code == s), None)
        typ       = " (L)" if (salle_obj and salle_obj.est_labo) else ""
        cap       = f"cap.{salle_obj.capacite}" if salle_obj else ""
        ax.text(si + 0.5, nb_creneaux + 0.55,
                f"{s}{typ}", ha="center", va="center",
                fontsize=8, fontweight="bold", color="#1A1A1A")
        ax.text(si + 0.5, nb_creneaux + 0.22,
                cap, ha="center", va="center",
                fontsize=6.5, color="#666666")

    # ── En-têtes lignes (créneaux) ────────────────────────────────────────
    for ci, c in enumerate(reversed(creneaux)):
        ax.text(-0.08, ci + 0.5,
                f"C{c}", ha="right", va="center",
                fontsize=8, fontweight="bold", color="#1A1A1A")

    # ── Légende filières ──────────────────────────────────────────────────
    handles = [
        mpatches.Patch(facecolor=PALETTE_FILIERES[f], edgecolor="#BBBBBB",
                       label=f"Filière {f}")
        for f in PALETTE_FILIERES if f != "AUTRE"
    ]
    handles.append(mpatches.Patch(facecolor=PALETTE_FILIERES["AUTRE"],
                                   edgecolor="#BBBBBB", label="Autre filière"))
    handles.append(mpatches.Patch(facecolor=COULEUR_LABO,
                                   edgecolor="#BBBBBB", label="Labo libre"))
    ax.legend(handles=handles, loc="lower center",
              bbox_to_anchor=(0.5, -0.12),
              ncol=min(len(handles), 4),
              fontsize=7.5, framealpha=0.9)

    ax.set_title("Planning des Examens — Créneau × Salle",
                 fontsize=13, fontweight="bold", pad=20)

    plt.tight_layout()
    plt.savefig(chemin_sortie, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  → Planning image sauvegardé : {chemin_sortie}")


def visualiser_audit(rapport: dict,
                      chemin_sortie: str = "audit_synthese.png"):
    """
    Génère un graphique de synthèse de l'audit :
      - Camembert statut global
      - Barres violations par type
    """
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.patch.set_facecolor("#F8F9FA")
    fig.suptitle("Synthèse de l'Audit du Planning",
                 fontsize=13, fontweight="bold")

    # ── Camembert statut ──────────────────────────────────────────────────
    ax1 = axes[0]
    ax1.set_facecolor("#F8F9FA")
    nb_oblig  = rapport["nb_obligatoires"]
    nb_souh   = rapport["nb_souhaitees"]
    nb_echecs = rapport["nb_echecs_affectation"]
    nb_ok     = 1 if rapport["conforme"] else 0

    labels  = []
    sizes   = []
    colors  = []
    if rapport["conforme"]:
        labels  = ["Conforme"]
        sizes   = [1]
        colors  = ["#58D68D"]
    else:
        if nb_oblig  > 0: labels.append(f"Viol. oblig. ({nb_oblig})");   sizes.append(nb_oblig);   colors.append("#E74C3C")
        if nb_souh   > 0: labels.append(f"Avert. ({nb_souh})");          sizes.append(nb_souh);    colors.append("#F39C12")
        if nb_echecs > 0: labels.append(f"Échecs affect. ({nb_echecs})");sizes.append(nb_echecs);  colors.append("#9B59B6")
        if not sizes:
            labels = ["Conforme"]; sizes = [1]; colors = ["#58D68D"]

    wedges, texts, autotexts = ax1.pie(
        sizes, labels=labels, colors=colors,
        autopct="%1.0f%%", startangle=90,
        wedgeprops={"edgecolor": "white", "linewidth": 2},
    )
    for t in texts:     t.set_fontsize(9)
    for t in autotexts: t.set_fontsize(9); t.set_fontweight("bold")
    ax1.set_title("Statut global", fontweight="bold")

    # ── Barres violations par code de règle ───────────────────────────────
    ax2 = axes[1]
    ax2.set_facecolor("#F8F9FA")

    compteur: dict[str, int] = {}
    for v in rapport["violations"]:
        compteur[v.code] = compteur.get(v.code, 0) + 1

    if compteur:
        codes   = sorted(compteur.keys())
        valeurs = [compteur[c] for c in codes]
        couleurs_barre = [
            "#E74C3C" if c.startswith("C") else "#F39C12"
            for c in codes
        ]
        barres = ax2.bar(codes, valeurs, color=couleurs_barre,
                         edgecolor="#333333", linewidth=0.7, width=0.5)
        for b, v in zip(barres, valeurs):
            ax2.text(b.get_x() + b.get_width() / 2,
                     b.get_height() + 0.05,
                     str(v), ha="center", va="bottom", fontweight="bold")
        ax2.set_xlabel("Code de contrainte")
        ax2.set_ylabel("Nombre de violations")
        ax2.set_title("Violations par contrainte", fontweight="bold")
        ax2.spines[["top", "right"]].set_visible(False)

        # Légende rouge/orange
        from matplotlib.lines import Line2D
        legend_elems = [
            mpatches.Patch(facecolor="#E74C3C", label="Obligatoire (C1–C5)"),
            mpatches.Patch(facecolor="#F39C12", label="Souhaitée (S1–S2)"),
        ]
        ax2.legend(handles=legend_elems, fontsize=8)
    else:
        ax2.text(0.5, 0.5, "✓ Aucune violation\ndétectée",
                 ha="center", va="center", fontsize=14,
                 color="#27AE60", fontweight="bold",
                 transform=ax2.transAxes)
        ax2.axis("off")

    plt.tight_layout()
    plt.savefig(chemin_sortie, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  → Audit synthèse sauvegardé : {chemin_sortie}")


# ─────────────────────────────────────────────────────────────────────────────
# 5.  RAPPORT DE SYNTHÈSE FINAL
# ─────────────────────────────────────────────────────────────────────────────

def afficher_synthese_finale(affectations: list, rapport: dict,
                              ues_info: dict, salles: list):
    """Affiche un résumé complet en console."""
    print("\n" + "=" * 60)
    print("  SYNTHÈSE FINALE DU PLANNING")
    print("=" * 60)

    nb_total   = len(affectations)
    nb_succes  = sum(1 for a in affectations if a.succes)
    nb_echecs  = nb_total - nb_succes
    creneaux   = sorted({a.creneau for a in affectations if a.succes})

    print(f"\n  UE planifiées       : {nb_succes}/{nb_total}")
    print(f"  UE non affectées    : {nb_echecs}")
    print(f"  Créneaux utilisés   : {len(creneaux)}")
    print(f"  Salles disponibles  : {len(salles)}")

    # Taux d'occupation par salle
    print(f"\n  {'Salle':<10} {'Type':<10} {'Capacité':>9} {'UE affectées':>14}")
    print(f"  {'─'*10} {'─'*10} {'─'*9} {'─'*14}")
    for salle in sorted(salles, key=lambda s: s.code):
        ues_salle = [a.ue_code for a in affectations
                     if a.succes and a.salle and a.salle.code == salle.code]
        typ = "Labo" if salle.est_labo else "Standard"
        print(f"  {salle.code:<10} {typ:<10} {salle.capacite:>9} "
              f"{'  '.join(ues_salle) if ues_salle else '—':>14}")

    # Statut audit
    statut = "✓ CONFORME" if rapport["conforme"] else "✗ NON CONFORME"
    print(f"\n  Statut audit        : {statut}")
    print(f"  Violations oblig.   : {rapport['nb_obligatoires']}")
    print(f"  Avertissements      : {rapport['nb_souhaitees']}")

    print("\n  Fichiers générés :")
    print("    planning_final.csv           — planning créneau × salle")
    print("    affectations_detaillees.csv  — détail par UE")
    print("    rapport_audit.csv            — violations détectées")
    print("    planning_visualisation.png   — grille visuelle du planning")
    print("    audit_synthese.png           — graphiques d'audit")
    print("=" * 60)


# ─────────────────────────────────────────────────────────────────────────────
# 6.  PROGRAMME PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def main(affectations_ext=None, rapport_ext=None, auditeur_ext=None,
         coloration_ext=None, graphe_ext=None):
    """
    Point d'entrée de planning.py.

    Peut être appelé directement ou recevoir les objets d'affectation.py.
    """
    print("=" * 60)
    print("  GROUPE C — Génération du Planning Final")
    print("  Projet : Planification d'Examens par Coloration")
    print("=" * 60)

    # ── Import ou recalcul des affectations ───────────────────────────────
    if affectations_ext is None:
        print("\n[1] Import complet depuis Groupes A, B et C (affectation)...")
        from affectation import main as affectation_main
        affectations, rapport, auditeur = affectation_main()
        from coloration import dsatur
        from graphe     import charger_donnees_exemple
        ues, etudiants, inscriptions = charger_donnees_exemple()
        graphe     = GrapheConflits(ues, inscriptions)
        coloration = dsatur(graphe)
    else:
        print("\n[1] Données reçues depuis affectation.py...")
        affectations = affectations_ext
        rapport      = rapport_ext
        coloration   = coloration_ext
        graphe       = graphe_ext

    salles   = salles_exemple()
    ues_info = ues_info_exemple()

    # ── Construction du tableau ───────────────────────────────────────────
    print("\n[2] Construction du tableau créneau × salle...")
    tableau, creneaux, salles_codes = construire_tableau(
        affectations, salles, ues_info
    )
    afficher_planning_console(tableau, creneaux, salles_codes, ues_info, salles)

    # ── Exports CSV ───────────────────────────────────────────────────────
    print("\n[3] Export CSV...")
    exporter_planning_csv(
        tableau, creneaux, salles_codes, ues_info, salles,
        chemin="planning_final.csv"
    )
    exporter_affectations_detaillees_csv(
        affectations, ues_info,
        chemin="affectations_detaillees.csv"
    )

    # ── Visualisations ────────────────────────────────────────────────────
    print("\n[4] Génération des visualisations...")
    visualiser_planning(
        tableau, creneaux, salles_codes, ues_info, salles, affectations,
        chemin_sortie="planning_visualisation.png"
    )

    # Rapport d'audit (réutilise le rapport déjà calculé)
    if rapport_ext is None:
        from affectation import MoteurAudit
        auditeur2 = MoteurAudit(affectations, ues_info, coloration, graphe)
        rapport2  = auditeur2.auditer()
    else:
        rapport2 = rapport_ext

    visualiser_audit(rapport2, chemin_sortie="audit_synthese.png")

    # ── Synthèse finale ───────────────────────────────────────────────────
    afficher_synthese_finale(affectations, rapport2, ues_info, salles)

    return tableau, creneaux, salles_codes


if __name__ == "__main__":
    main()
