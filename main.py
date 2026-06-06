"""
=============================================================================
 main.py — Groupe D : Intégration & Pipeline Global
 Projet : Planification d'Examens par Coloration de Graphes
 Niveau : L2 Informatique — Théorie des Graphes
=============================================================================

Script principal qui orchestre l'exécution complète du projet :

  ÉTAPE 1 (Groupe A) — Chargement des données + construction du graphe
  ÉTAPE 2 (Groupe B) — Coloration (Welsh-Powell et DSATUR) + benchmark
  ÉTAPE 3 (Groupe C) — Affectation des salles + audit des contraintes
  ÉTAPE 4 (Groupe C) — Génération du planning final + exports CSV/PNG

Tous les résultats sont sauvegardés dans le dossier output/.

Usage
-----
    python main.py                        # Données d'exemple intégrées
    python main.py --ues ues.csv --inscriptions inscriptions.csv
    python main.py --algo dsatur         # Forcer un algorithme (wp / dsatur)
    python main.py --tests               # Lancer la suite de tests unitaires

=============================================================================
"""

import os
import sys
import time
import argparse
import traceback

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

DOSSIER_OUTPUT = "output"
SEPARATEUR     = "=" * 60


def creer_dossier_output():
    """Crée le dossier de sortie si inexistant."""
    os.makedirs(DOSSIER_OUTPUT, exist_ok=True)


def chemin(nom_fichier: str) -> str:
    """Retourne le chemin complet dans le dossier output."""
    return os.path.join(DOSSIER_OUTPUT, nom_fichier)


# ─────────────────────────────────────────────────────────────────────────────
# BANNIÈRE
# ─────────────────────────────────────────────────────────────────────────────

def afficher_banniere():
    print(SEPARATEUR)
    print("  PLANIFICATION D'EXAMENS PAR COLORATION DE GRAPHES")
    print("  Projet L2 Informatique — Théorie des Graphes")
    print("  Université de Yaoundé | Année 2025-2026")
    print(SEPARATEUR)
    print()


# ─────────────────────────────────────────────────────────────────────────────
# ÉTAPE 1 — GROUPE A : GRAPHE
# ─────────────────────────────────────────────────────────────────────────────

def etape_1_graphe(chemin_ues=None, chemin_inscriptions=None):
    """
    Charge les données et construit le graphe de conflits.
    Retourne (graphe, ues, etudiants, inscriptions).
    """
    print(SEPARATEUR)
    print("  ÉTAPE 1 — Construction du graphe  [Groupe A]")
    print(SEPARATEUR)

    from graphe import (GrapheConflits, charger_donnees_exemple,
                         charger_depuis_csv, visualiser_graphe,
                         visualiser_matrice_adjacence,
                         exporter_aretes_csv, exporter_degres_csv)

    # Chargement
    t0 = time.perf_counter()
    if chemin_ues and chemin_inscriptions:
        print(f"  Chargement depuis CSV : {chemin_ues}, {chemin_inscriptions}")
        ues, etudiants, inscriptions = charger_depuis_csv(chemin_ues, chemin_inscriptions)
    else:
        print("  Utilisation des données d'exemple intégrées.")
        ues, etudiants, inscriptions = charger_donnees_exemple()

    print(f"  → {len(ues)} UE chargées, {len(etudiants)} étudiants")

    # Construction
    graphe = GrapheConflits(ues, inscriptions)
    duree  = (time.perf_counter() - t0) * 1000

    print(f"  → Graphe construit en {duree:.2f} ms")
    print(f"  → Sommets : {graphe.nb_sommets()}  |  Arêtes : {graphe.nb_aretes()}")
    print(f"  → Degré max : {graphe.degre_max()}  |  Densité : {graphe.densite()}")

    # Affichage console
    graphe.afficher_liste_adjacence()
    graphe.afficher_descripteurs()

    # Exports
    print("\n  Génération des fichiers Groupe A...")
    visualiser_graphe(
        graphe,
        chemin_sortie=chemin("graphe_conflits.png"),
        titre="Graphe de Conflits entre UE",
    )
    visualiser_matrice_adjacence(
        graphe,
        chemin_sortie=chemin("matrice_adjacence.png"),
    )
    exporter_aretes_csv(graphe,  chemin("aretes_graphe.csv"))
    exporter_degres_csv(graphe, chemin("degres_graphe.csv"))

    print(f"\n  ✓ Étape 1 terminée.")
    return graphe, ues, etudiants, inscriptions


# ─────────────────────────────────────────────────────────────────────────────
# ÉTAPE 2 — GROUPE B : COLORATION
# ─────────────────────────────────────────────────────────────────────────────

def etape_2_coloration(graphe, algorithme_force=None):
    """
    Exécute les algorithmes de coloration et le benchmark.
    Retourne (res_wp, res_ds, meilleur_resultat).
    """
    print()
    print(SEPARATEUR)
    print("  ÉTAPE 2 — Algorithmes de coloration  [Groupe B]")
    print(SEPARATEUR)

    from coloration import (welsh_powell, dsatur, benchmark,
                             visualiser_coloration,
                             visualiser_benchmark_comparatif,
                             visualiser_repartition_creneaux,
                             visualiser_scalabilite,
                             benchmark_multi_graphes)
    import random

    # Benchmark principal
    res_wp, res_ds = benchmark(graphe, nb_repetitions=200)

    # Sélection du meilleur algorithme
    if algorithme_force == "wp":
        meilleur = res_wp
        print(f"\n  Algorithme forcé : Welsh-Powell")
    elif algorithme_force == "dsatur":
        meilleur = res_ds
        print(f"\n  Algorithme forcé : DSATUR")
    else:
        meilleur = res_ds if res_ds.nb_couleurs <= res_wp.nb_couleurs else res_wp
        print(f"\n  Meilleur algorithme sélectionné : {meilleur.algorithme}")

    # Exports
    print("\n  Génération des fichiers Groupe B...")
    res_wp.vers_csv(chemin("coloration_welsh_powell.csv"))
    res_ds.vers_csv(chemin("coloration_dsatur.csv"))

    visualiser_coloration(graphe, res_wp, chemin("graphe_welsh_powell.png"))
    visualiser_coloration(graphe, res_ds, chemin("graphe_dsatur.png"))
    visualiser_benchmark_comparatif(res_wp, res_ds, chemin("benchmark_comparaison.png"))
    visualiser_repartition_creneaux(res_wp, res_ds, chemin("repartition_creneaux.png"))

    random.seed(42)
    resultats_multi = benchmark_multi_graphes([5, 10, 15, 20, 30, 50])
    visualiser_scalabilite(resultats_multi, chemin("benchmark_scalabilite.png"))

    print(f"\n  ✓ Étape 2 terminée.")
    return res_wp, res_ds, meilleur


# ─────────────────────────────────────────────────────────────────────────────
# ÉTAPE 3 — GROUPE C : AFFECTATION & AUDIT
# ─────────────────────────────────────────────────────────────────────────────

def etape_3_affectation(graphe, meilleur_resultat):
    """
    Affecte les salles et réalise l'audit.
    Retourne (affectations, rapport, auditeur, salles, ues_info).
    """
    print()
    print(SEPARATEUR)
    print("  ÉTAPE 3 — Affectation des salles & Audit  [Groupe C]")
    print(SEPARATEUR)

    from affectation import (MoteurAffectation, MoteurAudit,
                              salles_exemple, ues_info_exemple)

    salles   = salles_exemple()
    ues_info = ues_info_exemple()

    print(f"  → {len(salles)} salles disponibles")
    print(f"  → {len(ues_info)} UE avec infos logistiques")

    # Affectation
    moteur       = MoteurAffectation(salles, ues_info)
    affectations = moteur.affecter(meilleur_resultat.coloration)
    nb_succes    = sum(1 for a in affectations if a.succes)
    print(f"  → {nb_succes}/{len(affectations)} UE affectées avec succès")

    # Audit
    auditeur = MoteurAudit(
        affectations, ues_info,
        meilleur_resultat.coloration, graphe
    )
    rapport = auditeur.auditer()
    auditeur.afficher_rapport(rapport)

    # Exports
    auditeur.exporter_rapport_csv(chemin("rapport_audit.csv"))

    print(f"\n  ✓ Étape 3 terminée.")
    return affectations, rapport, auditeur, salles, ues_info


# ─────────────────────────────────────────────────────────────────────────────
# ÉTAPE 4 — GROUPE C : PLANNING FINAL
# ─────────────────────────────────────────────────────────────────────────────

def etape_4_planning(affectations, rapport, meilleur_resultat,
                      graphe, salles, ues_info):
    """
    Génère le planning final, les exports CSV et les visualisations.
    """
    print()
    print(SEPARATEUR)
    print("  ÉTAPE 4 — Planning final  [Groupe C]")
    print(SEPARATEUR)

    from planning import (construire_tableau, afficher_planning_console,
                           exporter_planning_csv,
                           exporter_affectations_detaillees_csv,
                           visualiser_planning, visualiser_audit,
                           afficher_synthese_finale)

    # Tableau
    tableau, creneaux, salles_codes = construire_tableau(
        affectations, salles, ues_info
    )
    afficher_planning_console(tableau, creneaux, salles_codes, ues_info, salles)

    # Exports CSV
    exporter_planning_csv(
        tableau, creneaux, salles_codes, ues_info, salles,
        chemin=chemin("planning_final.csv")
    )
    exporter_affectations_detaillees_csv(
        affectations, ues_info,
        chemin=chemin("affectations_detaillees.csv")
    )

    # Visualisations
    visualiser_planning(
        tableau, creneaux, salles_codes, ues_info, salles, affectations,
        chemin_sortie=chemin("planning_visualisation.png")
    )
    visualiser_audit(rapport, chemin_sortie=chemin("audit_synthese.png"))

    # Synthèse
    afficher_synthese_finale(affectations, rapport, ues_info, salles)

    print(f"\n  ✓ Étape 4 terminée.")
    return tableau, creneaux, salles_codes


# ─────────────────────────────────────────────────────────────────────────────
# SUITE DE TESTS UNITAIRES
# ─────────────────────────────────────────────────────────────────────────────

def lancer_tests():
    """
    Suite de tests automatiques pour valider chaque module.
    Affiche PASS / FAIL pour chaque test.
    """
    print(SEPARATEUR)
    print("  SUITE DE TESTS UNITAIRES")
    print(SEPARATEUR)

    nb_pass = 0
    nb_fail = 0

    def test(nom, condition, detail=""):
        nonlocal nb_pass, nb_fail
        if condition:
            print(f"  [PASS] {nom}")
            nb_pass += 1
        else:
            print(f"  [FAIL] {nom}" + (f" — {detail}" if detail else ""))
            nb_fail += 1

    # ── Groupe A ─────────────────────────────────────────────────────────
    print("\n  — Groupe A : GrapheConflits —")
    from graphe import GrapheConflits, charger_donnees_exemple
    ues, etudiants, inscriptions = charger_donnees_exemple()
    g = GrapheConflits(ues, inscriptions)

    test("Nb sommets = nb UE",
         g.nb_sommets() == len(ues),
         f"attendu {len(ues)}, obtenu {g.nb_sommets()}")

    test("Nb arêtes > 0",
         g.nb_aretes() > 0)

    test("Matrice symétrique",
         all(g.matrice[i][j] == g.matrice[j][i]
             for i in range(g.n) for j in range(g.n)))

    test("Diagonale nulle (pas d'arête avec soi-même)",
         all(g.matrice[i][i] == 0 for i in range(g.n)))

    test("Liste adj cohérente avec matrice",
         all(len(g.liste_adj[ue]) == sum(g.matrice[g.index[ue]])
             for ue in ues))

    test("Degré max >= degré moyen",
         g.degre_max() >= g.degre_moyen())

    test("Densité dans [0, 1]",
         0.0 <= g.densite() <= 1.0)

    # ── Groupe B ─────────────────────────────────────────────────────────
    print("\n  — Groupe B : Algorithmes de coloration —")
    from coloration import (welsh_powell, dsatur, est_coloration_valide,
                             ResultatColoration)

    col_wp = welsh_powell(g)
    col_ds = dsatur(g)

    test("Welsh-Powell : toutes les UE colorées",
         len(col_wp) == g.nb_sommets())

    test("DSATUR : toutes les UE colorées",
         len(col_ds) == g.nb_sommets())

    test("Welsh-Powell : coloration valide",
         est_coloration_valide(g, col_wp))

    test("DSATUR : coloration valide",
         est_coloration_valide(g, col_ds))

    test("Welsh-Powell : couleurs commencent à 0",
         min(col_wp.values()) == 0)

    test("DSATUR : couleurs commencent à 0",
         min(col_ds.values()) == 0)

    test("WP nb_couleurs > 0",
         max(col_wp.values()) + 1 > 0)

    # Graphe vide (0 arête) → 1 couleur suffit
    g_solo = GrapheConflits(["A"], {"E1": ["A"]})
    col_solo = welsh_powell(g_solo)
    test("Graphe 1 sommet → 1 couleur",
         max(col_solo.values()) + 1 == 1)

    # Graphe complet K3 → 3 couleurs minimum
    g_k3 = GrapheConflits(
        ["A", "B", "C"],
        {"E1": ["A", "B"], "E2": ["B", "C"], "E3": ["A", "C"]}
    )
    col_k3 = dsatur(g_k3)
    test("Graphe K3 → 3 couleurs (DSATUR)",
         max(col_k3.values()) + 1 == 3,
         f"obtenu {max(col_k3.values()) + 1}")

    # ── Groupe C ─────────────────────────────────────────────────────────
    print("\n  — Groupe C : Affectation & Audit —")
    from affectation import (MoteurAffectation, MoteurAudit,
                              salles_exemple, ues_info_exemple, Salle, UEInfo)

    salles   = salles_exemple()
    ues_info = ues_info_exemple()
    moteur   = MoteurAffectation(salles, ues_info)
    affs     = moteur.affecter(col_ds)

    test("Toutes les UE ont une affectation",
         len(affs) == g.nb_sommets())

    nb_succes = sum(1 for a in affs if a.succes)
    test(f"Au moins 1 UE affectée avec succès",
         nb_succes >= 1)

    # Vérif unicité salle par créneau
    from collections import defaultdict
    occ: dict = defaultdict(set)
    collision = False
    for a in affs:
        if a.succes and a.salle:
            k = (a.creneau, a.salle.code)
            if k in occ:
                collision = True
            occ[k].add(a.ue_code)
    test("Pas deux UE dans la même salle au même créneau",
         not collision)

    # Vérif capacité
    surcharge = any(
        a.succes and a.salle and ues_info.get(a.ue_code) and
        ues_info[a.ue_code].effectif > a.salle.capacite
        for a in affs
    )
    test("Aucune salle surchargée (capacité respectée)", not surcharge)

    # Vérif type labo
    labo_fail = any(
        a.succes and a.salle and ues_info.get(a.ue_code) and
        ues_info[a.ue_code].necessite_labo and not a.salle.est_labo
        for a in affs
    )
    test("UE labo → salle labo (C5 respectée)", not labo_fail)

    # Audit
    auditeur = MoteurAudit(affs, ues_info, col_ds, g)
    rapport  = auditeur.auditer()
    test("Audit : 0 violation obligatoire",
         rapport["nb_obligatoires"] == 0,
         f"violations : {rapport['nb_obligatoires']}")

    # ── Pipeline complet ──────────────────────────────────────────────────
    print("\n  — Pipeline complet —")
    try:
        # Recrée un mini-graphe et vérifie que le pipeline tourne sans erreur
        g_mini = GrapheConflits(
            ["M1", "M2", "M3"],
            {"S1": ["M1", "M2"], "S2": ["M2", "M3"], "S3": ["M1", "M3"]}
        )
        col_mini  = dsatur(g_mini)
        ues_mini  = {"M1": UEInfo("M1", 10), "M2": UEInfo("M2", 8), "M3": UEInfo("M3", 5)}
        sal_mini  = [Salle("S101", 20), Salle("S102", 15)]
        mot_mini  = MoteurAffectation(sal_mini, ues_mini)
        affs_mini = mot_mini.affecter(col_mini)
        aud_mini  = MoteurAudit(affs_mini, ues_mini, col_mini, g_mini)
        rap_mini  = aud_mini.auditer()
        test("Pipeline mini (3 UE) sans exception", True)
        test("Pipeline mini : audit valide",
             rap_mini["nb_obligatoires"] == 0)
    except Exception as e:
        test("Pipeline mini sans exception", False, str(e))

    # ── Résumé ────────────────────────────────────────────────────────────
    print()
    print(SEPARATEUR)
    print(f"  RÉSULTATS : {nb_pass} PASS  |  {nb_fail} FAIL")
    if nb_fail == 0:
        print("  ✓ Tous les tests passent — pipeline prêt pour la soutenance.")
    else:
        print("  ✗ Certains tests échouent — corriger avant la remise.")
    print(SEPARATEUR)

    return nb_fail == 0


# ─────────────────────────────────────────────────────────────────────────────
# RÉCAPITULATIF FINAL
# ─────────────────────────────────────────────────────────────────────────────

def afficher_recap_final(res_wp, res_ds, meilleur, rapport,
                          t_total, dossier=DOSSIER_OUTPUT):
    print()
    print(SEPARATEUR)
    print("  RÉCAPITULATIF FINAL DU PIPELINE")
    print(SEPARATEUR)

    print(f"\n  Algorithme retenu      : {meilleur.algorithme}")
    print(f"  Créneaux nécessaires   : {meilleur.nb_couleurs}")
    print(f"  Statut audit           : {'✓ CONFORME' if rapport['conforme'] else '✗ NON CONFORME'}")
    print(f"  Violations oblig.      : {rapport['nb_obligatoires']}")
    print(f"  Avertissements         : {rapport['nb_souhaitees']}")
    print(f"  Temps total pipeline   : {t_total:.2f} s")

    print(f"\n  Fichiers générés dans '{dossier}/' :")
    fichiers = [
        ("graphe_conflits.png",        "Visualisation du graphe"),
        ("matrice_adjacence.png",      "Matrice d'adjacence"),
        ("graphe_welsh_powell.png",    "Graphe coloré (Welsh-Powell)"),
        ("graphe_dsatur.png",          "Graphe coloré (DSATUR)"),
        ("benchmark_comparaison.png",  "Benchmark comparatif"),
        ("benchmark_scalabilite.png",  "Courbes de scalabilité"),
        ("repartition_creneaux.png",   "Répartition UE par créneau"),
        ("planning_visualisation.png", "Grille du planning"),
        ("audit_synthese.png",         "Synthèse de l'audit"),
        ("aretes_graphe.csv",          "Liste des arêtes"),
        ("degres_graphe.csv",          "Degrés par UE"),
        ("coloration_welsh_powell.csv","Coloration Welsh-Powell"),
        ("coloration_dsatur.csv",      "Coloration DSATUR"),
        ("planning_final.csv",         "Planning créneau × salle"),
        ("affectations_detaillees.csv","Détail affectations par UE"),
        ("rapport_audit.csv",          "Rapport d'audit"),
    ]
    for nom, desc in fichiers:
        p = os.path.join(dossier, nom)
        existe = "✓" if os.path.exists(p) else "✗"
        print(f"    {existe}  {nom:<38}  {desc}")

    print(SEPARATEUR)


# ─────────────────────────────────────────────────────────────────────────────
# ARGUMENTS CLI
# ─────────────────────────────────────────────────────────────────────────────

def parser_arguments():
    p = argparse.ArgumentParser(
        description="Pipeline complet : Coloration de graphes → Planning d'examens"
    )
    p.add_argument("--ues",            help="Chemin vers ues.csv")
    p.add_argument("--inscriptions",   help="Chemin vers inscriptions.csv")
    p.add_argument("--algo",           choices=["wp", "dsatur"],
                   help="Forcer l'algorithme : wp (Welsh-Powell) ou dsatur")
    p.add_argument("--tests",          action="store_true",
                   help="Lancer la suite de tests unitaires")
    p.add_argument("--output",         default=DOSSIER_OUTPUT,
                   help=f"Dossier de sortie (défaut : {DOSSIER_OUTPUT})")
    return p.parse_args()


# ─────────────────────────────────────────────────────────────────────────────
# PROGRAMME PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def main():
    global DOSSIER_OUTPUT

    args = parser_arguments()
    DOSSIER_OUTPUT = args.output
    creer_dossier_output()

    afficher_banniere()

    # Mode tests uniquement
    if args.tests:
        succes = lancer_tests()
        sys.exit(0 if succes else 1)

    t_debut = time.perf_counter()

    try:
        # Étape 1 — Graphe
        graphe, ues, etudiants, inscriptions = etape_1_graphe(
            chemin_ues=args.ues,
            chemin_inscriptions=args.inscriptions,
        )

        # Étape 2 — Coloration
        res_wp, res_ds, meilleur = etape_2_coloration(
            graphe,
            algorithme_force=args.algo,
        )

        # Étape 3 — Affectation & Audit
        affectations, rapport, auditeur, salles, ues_info = etape_3_affectation(
            graphe, meilleur
        )

        # Étape 4 — Planning
        tableau, creneaux, salles_codes = etape_4_planning(
            affectations, rapport, meilleur,
            graphe, salles, ues_info
        )

        t_total = time.perf_counter() - t_debut

        afficher_recap_final(res_wp, res_ds, meilleur, rapport, t_total, DOSSIER_OUTPUT)

        print(f"\n  Pipeline terminé avec succès en {t_total:.2f} s")
        print(f"  Résultats dans : {os.path.abspath(DOSSIER_OUTPUT)}/\n")

    except Exception as e:
        print(f"\n  ERREUR : {e}")
        traceback.print_exc()
        print("\n  Le pipeline s'est arrêté. Vérifiez les fichiers d'entrée.")
        sys.exit(1)


if __name__ == "__main__":
    main()
