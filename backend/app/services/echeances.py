"""Calcul de la coloration des courriers selon la date limite.

Règle (PRD-01 §5.7) :
- Noir : date_limite < today
- Rouge dégradé (clair → foncé) : 0 ≤ date_limite - today ≤ 4 jours
- Vert : date_limite > today + 4 ou date_limite IS NULL
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

CouleurEcheance = Literal["noir", "rouge-clair", "rouge", "rouge-fonce", "vert"]


@dataclass(frozen=True, slots=True)
class StatutEcheance:
    """Résultat du calcul de coloration pour une date limite."""

    couleur: CouleurEcheance
    jours_restants: int | None  # None si pas de date limite ; négatif si dépassé


def calculer_statut_echeance(
    date_limite: date | None,
    *,
    aujourd_hui: date | None = None,
    seuil_alerte_jours: int = 4,
) -> StatutEcheance:
    """Détermine la couleur d'affichage pour un courrier.

    Args:
        date_limite : date limite de traitement, ou None si pas d'échéance.
        aujourd_hui : date de référence (injectable pour les tests).
        seuil_alerte_jours : nombre de jours avant échéance déclenchant le rouge.

    Returns:
        Un `StatutEcheance` avec la couleur et le nombre de jours restants.
    """
    if date_limite is None:
        return StatutEcheance(couleur="vert", jours_restants=None)

    today = aujourd_hui or date.today()
    delta = (date_limite - today).days

    if delta < 0:
        return StatutEcheance(couleur="noir", jours_restants=delta)
    if delta > seuil_alerte_jours:
        return StatutEcheance(couleur="vert", jours_restants=delta)

    # 0 ≤ delta ≤ seuil → dégradé de rouge (plus c'est proche, plus c'est foncé)
    # 4 jours → rouge-clair
    # 2-3 jours → rouge
    # 0-1 jour → rouge-fonce
    if delta >= 4:
        couleur: CouleurEcheance = "rouge-clair"
    elif delta >= 2:
        couleur = "rouge"
    else:
        couleur = "rouge-fonce"
    return StatutEcheance(couleur=couleur, jours_restants=delta)
