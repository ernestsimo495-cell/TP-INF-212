"""
=============================================================================
 affectation.py — Groupe C : Affectation des Salles & Audit
 Projet : Planification d'Examens par Coloration de Graphes
 Niveau : L2 Informatique — Théorie des Graphes
=============================================================================

Ce fichier implémente :
  1. Les structures de données : Salle, UE enrichie, Affectation
  2. Le moteur d'affectation des salles
       → Respecte capacité, type (standard/labo), disponibilité
  3. Le moteur d'audit automatique
       → Vérifie toutes les contraintes obligatoires et souhaitées
  4. Rapport d'audit détaillé (console + CSV)

=============================================================================
"""

import csv
from dataclasses import dataclass, field
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# 1.  STRUCTURES DE DONNÉES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Salle:
    """
    Représente une salle d'examen physique.

    Attributs
    ---------
    code        : identifiant unique (ex : "A101", "LABO1")
    capacite    : nombre maximum d'étudiants accueillis
    est_labo    : True si c'est un laboratoire informatique
    """
    code     : str
    capacite : int
    est_labo : bool = False

    def __str__(self):
        typ = "Labo" if self.est_labo else "Standard"
        return f"{self.code} ({typ}, cap.{self.capacite})"


@dataclass
class UEInfo:
    """
    Enrichit une UE avec ses contraintes logistiques.

    Attributs
    ---------
    code            : code de l'UE (ex : "ALGO")
    effectif        : nombre d'étudiants inscrits
    necessite_labo  : True si l'épreuve requiert un laboratoire
    surveillant     : identifiant de l'enseignant-surveillant
    filiere         : filière à laquelle appartient l'UE
    """
    code           : str
    effectif       : int
    necessite_labo : bool = False
    surveillant    : str  = ""
    filiere        : str  = ""

    def __str__(self):
        return (f"{self.code} | effectif={self.effectif} | "
                f"labo={self.necessite_labo} | surv={self.surveillant} | "
                f"filiere={self.filiere}")


@dataclass
class Affectation:
    """
    Résultat de l'affectation d'une UE : créneau + salle.

    Attributs
    ---------
    ue_code  : code de l'UE
    creneau  : numéro du créneau (commence à 1)
    salle    : objet Salle attribué (None si non trouvé)
    succes   : True si une salle valide a été trouvée
    raison   : message d'erreur si succes == False
    """
    ue_code : str
    creneau : int
    salle   : Optional[Salle] = None
    succes  : bool            = False
    raison  : str             = ""

    def __str__(self):
        if self.succes:
            return (f"  {self.ue_code:<12} → Créneau {self.creneau:>2} | "
                    f"Salle {self.salle.code}")
        return (f"  {self.ue_code:<12} → Créneau {self.creneau:>2} | "
                f"✗ ÉCHEC : {self.raison}")


# ─────────────────────────────────────────────────────────────────────────────
# 2.  DONNÉES D'EXEMPLE
# ─────────────────────────────────────────────────────────────────────────────

def salles_exemple() -> list:
    """
    Retourne une liste de salles d'exemple.
    Remplacez ces données par votre vrai référentiel de salles.
    """
    return [
        Salle("A101",  30, est_labo=False),
        Salle("A102",  40, est_labo=False),
        Salle("B201",  50, est_labo=False),
        Salle("B202",  25, est_labo=False),
        Salle("C301",  60, est_labo=False),
        Salle("LABO1", 30, est_labo=True),
        Salle("LABO2", 25, est_labo=True),
    ]


def ues_info_exemple() -> dict:
    """
    Retourne un dict {code_ue -> UEInfo} avec les infos logistiques.
    Remplacez ces données par votre vrai référentiel d'UE.

    Les codes doivent correspondre à ceux de graphe.py.
    """
    return {
        "MATHS1":  UEInfo("MATHS1",  35, necessite_labo=False, surveillant="PROF_A", filiere="INFO"),
        "ALGO":    UEInfo("ALGO",    28, necessite_labo=False, surveillant="PROF_B", filiere="INFO"),
        "PROG":    UEInfo("PROG",    22, necessite_labo=True,  surveillant="PROF_C", filiere="INFO"),
        "RESEAU":  UEInfo("RESEAU",  18, necessite_labo=False, surveillant="PROF_D", filiere="RESEAU"),
        "BD":      UEInfo("BD",      30, necessite_labo=True,  surveillant="PROF_E", filiere="INFO"),
        "SYS":     UEInfo("SYS",     20, necessite_labo=False, surveillant="PROF_F", filiere="RESEAU"),
        "PHYS":    UEInfo("PHYS",    25, necessite_labo=False, surveillant="PROF_G", filiere="SCIENCE"),
        "ANGLAIS": UEInfo("ANGLAIS", 40, necessite_labo=False, surveillant="PROF_H", filiere="LANGUE"),
        "STAT":    UEInfo("STAT",    15, necessite_labo=False, surveillant="PROF_A", filiere="SCIENCE"),
        "GRAPH":   UEInfo("GRAPH",   20, necessite_labo=False, surveillant="PROF_B", filiere="INFO"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 3.  MOTEUR D'AFFECTATION DES SALLES
# ─────────────────────────────────────────────────────────────────────────────

class MoteurAffectation:
    """
    Attribue une salle à chaque UE en respectant :
      - la capacité de la salle >= effectif de l'UE
      - le type de salle (labo si nécessaire)
      - l'unicité : une salle ne peut accueillir qu'un examen par créneau

    Stratégie : pour chaque UE (triée par effectif décroissant dans son
    créneau), on cherche la salle disponible de capacité minimale suffisante
    (Best Fit) afin de minimiser le gaspillage.
    """

    def __init__(self, salles: list, ues_info: dict):
        """
        Paramètres
        ----------
        salles   : liste d'objets Salle
        ues_info : dict {code_ue -> UEInfo}
        """
        self.salles   = salles
        self.ues_info = ues_info

        # occupation[creneau][salle_code] = True si la salle est prise
        self.occupation: dict[int, dict[str, bool]] = {}

    def _salle_disponible(self, creneau: int, salle: Salle) -> bool:
        """Retourne True si la salle est libre à ce créneau."""
        return not self.occupation.get(creneau, {}).get(salle.code, False)

    def _reserver(self, creneau: int, salle: Salle):
        """Marque la salle comme occupée à ce créneau."""
        self.occupation.setdefault(creneau, {})[salle.code] = True

    def _choisir_salle(self, creneau: int, ue_info: UEInfo) -> Optional[Salle]:
        """
        Stratégie Best Fit :
        Parmi toutes les salles disponibles au créneau donné, compatibles
        en type et en capacité, retourner celle dont la capacité est la
        plus proche (par excès) de l'effectif → minimise le gaspillage.
        """
        candidates = []
        for salle in self.salles:
            # Filtre 1 : type (labo requis → labo seulement)
            if ue_info.necessite_labo and not salle.est_labo:
                continue
            # Filtre 2 : capacité suffisante
            if salle.capacite < ue_info.effectif:
                continue
            # Filtre 3 : disponibilité au créneau
            if not self._salle_disponible(creneau, salle):
                continue
            candidates.append(salle)

        if not candidates:
            return None

        # Sélection Best Fit : capacité minimale parmi les candidates
        return min(candidates, key=lambda s: s.capacite)

    def affecter(self, coloration: dict) -> list:
        """
        Effectue l'affectation complète pour toutes les UE.

        Paramètre
        ---------
        coloration : dict {code_ue -> numéro_créneau} (depuis coloration.py)
                     Les créneaux commencent à 0.

        Retourne
        --------
        Liste d'objets Affectation, triée par créneau puis par UE.
        """
        resultats = []

        # Regrouper les UE par créneau
        creneaux: dict[int, list] = {}
        for ue, creneau in coloration.items():
            creneaux.setdefault(creneau, []).append(ue)

        # Pour chaque créneau, traiter les UE par effectif décroissant
        # (les plus grandes UE ont priorité sur les grandes salles)
        for creneau in sorted(creneaux.keys()):
            ues_du_creneau = creneaux[creneau]
            ues_du_creneau.sort(
                key=lambda u: self.ues_info.get(u, UEInfo(u, 0)).effectif,
                reverse=True
            )

            for ue_code in ues_du_creneau:
                ue_info = self.ues_info.get(ue_code)
                if ue_info is None:
                    resultats.append(Affectation(
                        ue_code, creneau + 1, succes=False,
                        raison=f"UEInfo manquante pour '{ue_code}'"
                    ))
                    continue

                salle = self._choisir_salle(creneau, ue_info)

                if salle:
                    self._reserver(creneau, salle)
                    resultats.append(Affectation(
                        ue_code, creneau + 1, salle=salle, succes=True
                    ))
                else:
                    # Diagnostic de l'échec
                    raison = self._diagnostiquer_echec(creneau, ue_info)
                    resultats.append(Affectation(
                        ue_code, creneau + 1, succes=False, raison=raison
                    ))

        return sorted(resultats, key=lambda a: (a.creneau, a.ue_code))

    def _diagnostiquer_echec(self, creneau: int, ue_info: UEInfo) -> str:
        """Explique pourquoi aucune salle n'a pu être attribuée."""
        # Salles du bon type
        bon_type = [s for s in self.salles
                    if not ue_info.necessite_labo or s.est_labo]
        if not bon_type:
            return f"Aucune salle {'labo' if ue_info.necessite_labo else 'standard'} disponible"

        # Salles assez grandes
        assez_grandes = [s for s in bon_type if s.capacite >= ue_info.effectif]
        if not assez_grandes:
            max_cap = max(s.capacite for s in bon_type)
            return (f"Effectif {ue_info.effectif} > capacité max "
                    f"{'labo' if ue_info.necessite_labo else 'standard'} ({max_cap})")

        # Salles disponibles au créneau
        return (f"Toutes les salles compatibles sont déjà prises au créneau {creneau + 1}")


# ─────────────────────────────────────────────────────────────────────────────
# 4.  MOTEUR D'AUDIT
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Violation:
    """Représente une violation de contrainte détectée lors de l'audit."""
    type_contrainte : str    # "OBLIGATOIRE" ou "SOUHAITEE"
    code            : str    # identifiant court de la règle
    message         : str    # description détaillée
    ues_impliquees  : list = field(default_factory=list)

    def __str__(self):
        ues = ", ".join(self.ues_impliquees) if self.ues_impliquees else "—"
        return f"  [{self.type_contrainte}] {self.code} : {self.message} (UE : {ues})"


class MoteurAudit:
    """
    Vérifie le respect de toutes les contraintes après affectation.

    Contraintes obligatoires vérifiées :
      C1 — Un étudiant ne compose qu'une UE par créneau
      C2 — Une salle = un examen par créneau
      C3 — Capacité de la salle respectée
      C4 — Un surveillant n'est pas dans deux salles en même temps
      C5 — Labo requis → salle labo attribuée

    Contraintes souhaitées vérifiées :
      S1 — Espacement entre examens d'une même filière (pas deux consécutifs)
      S2 — Équilibre de la charge par créneau
    """

    def __init__(self, affectations: list, ues_info: dict,
                 coloration: dict, graphe=None):
        """
        Paramètres
        ----------
        affectations : liste d'objets Affectation
        ues_info     : dict {code_ue -> UEInfo}
        coloration   : dict {code_ue -> numéro_créneau} (0-indexé)
        graphe       : GrapheConflits (optionnel, pour C1)
        """
        self.affectations = {a.ue_code: a for a in affectations}
        self.ues_info     = ues_info
        self.coloration   = coloration
        self.graphe       = graphe
        self.violations   : list[Violation] = []

        # Index créneau → liste d'UE (1-indexé)
        self.creneau_ues: dict[int, list] = {}
        for ue, c in coloration.items():
            self.creneau_ues.setdefault(c + 1, []).append(ue)

    # ── Vérifications obligatoires ────────────────────────────────────────

    def _verifier_c1_un_examen_par_etudiant(self):
        """
        C1 : Si deux UE voisines (conflit d'étudiants) sont au même créneau
             → violation. Normalement garanti par la coloration, mais on
             re-vérifie ici comme filet de sécurité.
        """
        if self.graphe is None:
            return
        for ue in self.coloration:
            for voisin in self.graphe.voisins(ue):
                if (voisin in self.coloration and
                        self.coloration[ue] == self.coloration[voisin] and
                        ue < voisin):
                    self.violations.append(Violation(
                        "OBLIGATOIRE", "C1",
                        f"UE '{ue}' et '{voisin}' partagent des étudiants mais sont au même créneau",
                        [ue, voisin]
                    ))

    def _verifier_c2_unicite_salle(self):
        """C2 : Une salle ne peut accueillir qu'un examen par créneau."""
        for creneau, ues in self.creneau_ues.items():
            salles_utilisees: dict[str, str] = {}   # salle_code → ue_code
            for ue in ues:
                aff = self.affectations.get(ue)
                if aff and aff.succes and aff.salle:
                    code_salle = aff.salle.code
                    if code_salle in salles_utilisees:
                        self.violations.append(Violation(
                            "OBLIGATOIRE", "C2",
                            f"Salle '{code_salle}' utilisée pour '{salles_utilisees[code_salle]}' "
                            f"ET '{ue}' au créneau {creneau}",
                            [salles_utilisees[code_salle], ue]
                        ))
                    else:
                        salles_utilisees[code_salle] = ue

    def _verifier_c3_capacite(self):
        """C3 : L'effectif de l'UE ne dépasse pas la capacité de la salle."""
        for ue, aff in self.affectations.items():
            if not aff.succes or aff.salle is None:
                continue
            info = self.ues_info.get(ue)
            if info and info.effectif > aff.salle.capacite:
                self.violations.append(Violation(
                    "OBLIGATOIRE", "C3",
                    f"'{ue}' : effectif {info.effectif} > capacité salle "
                    f"'{aff.salle.code}' ({aff.salle.capacite})",
                    [ue]
                ))

    def _verifier_c4_surveillant(self):
        """C4 : Un surveillant ne surveille pas deux salles en même temps."""
        for creneau, ues in self.creneau_ues.items():
            surv_ues: dict[str, str] = {}   # surveillant → ue_code
            for ue in ues:
                info = self.ues_info.get(ue)
                if not info or not info.surveillant:
                    continue
                surv = info.surveillant
                if surv in surv_ues:
                    self.violations.append(Violation(
                        "OBLIGATOIRE", "C4",
                        f"Surveillant '{surv}' affecté à '{surv_ues[surv]}' "
                        f"ET '{ue}' au créneau {creneau}",
                        [surv_ues[surv], ue]
                    ))
                else:
                    surv_ues[surv] = ue

    def _verifier_c5_labo(self):
        """C5 : Si l'UE nécessite un labo, la salle attribuée doit être un labo."""
        for ue, aff in self.affectations.items():
            if not aff.succes or aff.salle is None:
                continue
            info = self.ues_info.get(ue)
            if info and info.necessite_labo and not aff.salle.est_labo:
                self.violations.append(Violation(
                    "OBLIGATOIRE", "C5",
                    f"'{ue}' nécessite un labo mais est affectée à la salle "
                    f"standard '{aff.salle.code}'",
                    [ue]
                ))

    # ── Vérifications souhaitées ──────────────────────────────────────────

    def _verifier_s1_espacement_filiere(self):
        """
        S1 : Deux examens d'une même filière ne doivent pas être dans des
             créneaux consécutifs (au moins un créneau libre entre eux).
        """
        filiere_creneaux: dict[str, list] = {}
        for ue, info in self.ues_info.items():
            if info.filiere and ue in self.coloration:
                creneau = self.coloration[ue] + 1   # 1-indexé
                filiere_creneaux.setdefault(info.filiere, []).append((creneau, ue))

        for filiere, items in filiere_creneaux.items():
            items.sort()   # trier par créneau
            for i in range(len(items) - 1):
                c1, ue1 = items[i]
                c2, ue2 = items[i + 1]
                if c2 - c1 == 1:    # créneaux consécutifs
                    self.violations.append(Violation(
                        "SOUHAITEE", "S1",
                        f"Filière '{filiere}' : '{ue1}' (créneau {c1}) et "
                        f"'{ue2}' (créneau {c2}) sont consécutifs",
                        [ue1, ue2]
                    ))

    def _verifier_s2_equilibre_charge(self, seuil_desequilibre: float = 0.5):
        """
        S2 : Le nombre d'examens par créneau doit être aussi uniforme que
             possible. On signale si un créneau contient plus de (1 + seuil)
             fois la moyenne.
        """
        if not self.creneau_ues:
            return
        charges = {c: len(ues) for c, ues in self.creneau_ues.items()}
        moyenne = sum(charges.values()) / len(charges)
        for creneau, nb in charges.items():
            if nb > moyenne * (1 + seuil_desequilibre):
                self.violations.append(Violation(
                    "SOUHAITEE", "S2",
                    f"Créneau {creneau} surchargé : {nb} examens "
                    f"(moyenne = {moyenne:.1f})",
                    list(self.creneau_ues[creneau])
                ))

    # ── Rapport d'audit ───────────────────────────────────────────────────

    def auditer(self) -> dict:
        """
        Lance toutes les vérifications et retourne un rapport structuré.

        Retourne
        --------
        dict avec :
            "violations"         : liste de Violation
            "nb_obligatoires"    : int
            "nb_souhaitees"      : int
            "nb_echecs_affectation" : int
            "conforme"           : bool (True si 0 violation obligatoire
                                         et 0 échec d'affectation)
        """
        self.violations = []   # reset

        # Contraintes obligatoires
        self._verifier_c1_un_examen_par_etudiant()
        self._verifier_c2_unicite_salle()
        self._verifier_c3_capacite()
        self._verifier_c4_surveillant()
        self._verifier_c5_labo()

        # Contraintes souhaitées
        self._verifier_s1_espacement_filiere()
        self._verifier_s2_equilibre_charge()

        nb_oblig  = sum(1 for v in self.violations if v.type_contrainte == "OBLIGATOIRE")
        nb_souh   = sum(1 for v in self.violations if v.type_contrainte == "SOUHAITEE")
        nb_echecs = sum(1 for a in self.affectations.values() if not a.succes)

        return {
            "violations"              : self.violations,
            "nb_obligatoires"         : nb_oblig,
            "nb_souhaitees"           : nb_souh,
            "nb_echecs_affectation"   : nb_echecs,
            "conforme"                : (nb_oblig == 0 and nb_echecs == 0),
        }

    def afficher_rapport(self, rapport: dict):
        """Affiche le rapport d'audit complet dans la console."""
        print("\n" + "=" * 60)
        print("  RAPPORT D'AUDIT")
        print("=" * 60)

        statut = "✓ CONFORME" if rapport["conforme"] else "✗ NON CONFORME"
        print(f"\n  Statut global : {statut}")
        print(f"  Violations obligatoires  : {rapport['nb_obligatoires']}")
        print(f"  Violations souhaitées    : {rapport['nb_souhaitees']}")
        print(f"  Échecs d'affectation     : {rapport['nb_echecs_affectation']}")

        # Affectations réussies / échouées
        print(f"\n{'─'*60}")
        print("  AFFECTATIONS")
        print(f"{'─'*60}")
        nb_succes = sum(1 for a in self.affectations.values() if a.succes)
        nb_total  = len(self.affectations)
        print(f"  {nb_succes}/{nb_total} UE affectées avec succès\n")
        for a in sorted(self.affectations.values(), key=lambda x: (x.creneau, x.ue_code)):
            print(str(a))

        # Violations obligatoires
        oblig = [v for v in rapport["violations"] if v.type_contrainte == "OBLIGATOIRE"]
        if oblig:
            print(f"\n{'─'*60}")
            print("  VIOLATIONS OBLIGATOIRES")
            print(f"{'─'*60}")
            for v in oblig:
                print(str(v))
        else:
            print(f"\n  ✓ Aucune violation obligatoire détectée.")

        # Violations souhaitées
        souh = [v for v in rapport["violations"] if v.type_contrainte == "SOUHAITEE"]
        if souh:
            print(f"\n{'─'*60}")
            print("  AVERTISSEMENTS (contraintes souhaitées)")
            print(f"{'─'*60}")
            for v in souh:
                print(str(v))
        else:
            print(f"\n  ✓ Aucun avertissement sur les contraintes souhaitées.")

        print("\n" + "=" * 60)

    def exporter_rapport_csv(self, chemin: str = "rapport_audit.csv"):
        """Exporte le rapport d'audit dans un fichier CSV."""
        with open(chemin, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Type", "Code", "Message", "UE_impliquees"])
            for v in self.violations:
                writer.writerow([
                    v.type_contrainte,
                    v.code,
                    v.message,
                    "; ".join(v.ues_impliquees),
                ])
            if not self.violations:
                writer.writerow(["INFO", "OK", "Aucune violation détectée", ""])
        print(f"  → Rapport audit exporté : {chemin}")


# ─────────────────────────────────────────────────────────────────────────────
# 5.  PROGRAMME PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def main(coloration_externe: dict = None, graphe_externe=None):
    """
    Point d'entrée du module affectation.

    Paramètres optionnels
    ---------------------
    coloration_externe : dict {code_ue -> créneau} venant de coloration.py
    graphe_externe     : GrapheConflits venant de graphe.py

    Si non fournis, les données d'exemple sont utilisées.
    """
    print("=" * 60)
    print("  GROUPE C — Affectation des Salles & Audit")
    print("  Projet : Planification d'Examens par Coloration")
    print("=" * 60)

    # ── Récupération du graphe et de la coloration ────────────────────────
    if coloration_externe is None or graphe_externe is None:
        print("\n[1] Import des résultats des Groupes A et B...")
        from graphe import GrapheConflits, charger_donnees_exemple
        from coloration import dsatur
        ues, etudiants, inscriptions = charger_donnees_exemple()
        graphe     = GrapheConflits(ues, inscriptions)
        coloration = dsatur(graphe)
        print(f"    → Graphe : {graphe.nb_sommets()} sommets, "
              f"{graphe.nb_aretes()} arêtes")
        print(f"    → Coloration DSATUR : {max(coloration.values()) + 1} créneaux")
    else:
        graphe     = graphe_externe
        coloration = coloration_externe

    # ── Chargement des données logistiques ───────────────────────────────
    print("\n[2] Chargement des données logistiques...")
    salles   = salles_exemple()
    ues_info = ues_info_exemple()
    print(f"    → {len(salles)} salles disponibles")
    print(f"    → {len(ues_info)} UE avec infos logistiques")

    # ── Affectation des salles ────────────────────────────────────────────
    print("\n[3] Affectation des salles...")
    moteur       = MoteurAffectation(salles, ues_info)
    affectations = moteur.affecter(coloration)
    nb_succes    = sum(1 for a in affectations if a.succes)
    print(f"    → {nb_succes}/{len(affectations)} UE affectées avec succès")

    # ── Audit ─────────────────────────────────────────────────────────────
    print("\n[4] Audit des contraintes...")
    auditeur = MoteurAudit(affectations, ues_info, coloration, graphe)
    rapport  = auditeur.auditer()
    auditeur.afficher_rapport(rapport)

    # ── Export CSV du rapport d'audit ────────────────────────────────────
    print("\n[5] Export CSV...")
    auditeur.exporter_rapport_csv("rapport_audit.csv")

    return affectations, rapport, auditeur


if __name__ == "__main__":
    main()
