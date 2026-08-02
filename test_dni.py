#!/usr/bin/env python3
"""
Self-check pour la régulation DNI proportionnelle.
Lance avec : python3 test_dni.py
"""

def calc_taux_dni(solar_dni, dni_seuil, dni_hyst, last_taux_dni, facade_exposee, t_int, temp_int_high):
    """Réplique la logique du moteur pour le calcul du taux DNI."""
    if facade_exposee and t_int > temp_int_high and solar_dni > (dni_seuil + dni_hyst):
        return max(0.0, 1.0 - dni_seuil / solar_dni)
    elif facade_exposee and solar_dni > dni_seuil:
        return last_taux_dni  # hystérésis : maintien
    else:
        return 0.0

# --- Tests ---
CIBLE, HYST, T_INT_HIGH = 550.0, 50.0, 23.5

def check(desc, got, expected, tol=0.005):
    ok = abs(got - expected) <= tol
    print(f"{'✅' if ok else '❌'} {desc}: {got:.3f} (attendu ≈ {expected:.3f})")
    assert ok, f"ÉCHEC : {got} != {expected}"

# Cas nominal : DNI 700 > 600, t_int > seuil, façade exposée → ~21.4%
check(
    "DNI 700 W/m², t_int 24°C, façade exposée",
    calc_taux_dni(700, CIBLE, HYST, 0.0, True, 24.0, T_INT_HIGH),
    1.0 - 550/700  # ≈ 0.214
)

# Cas t_int trop basse → 0% même si DNI élevé
check(
    "DNI 700 W/m², t_int 22°C (sous seuil) → 0",
    calc_taux_dni(700, CIBLE, HYST, 0.0, True, 22.0, T_INT_HIGH),
    0.0
)

# Cas DNI sous la cible → 0%
check(
    "DNI 500 W/m² (sous cible 550) → 0",
    calc_taux_dni(500, CIBLE, HYST, 0.0, True, 24.0, T_INT_HIGH),
    0.0
)

# Cas hystérésis : DNI 580 (entre 550 et 600), last_taux_dni = 0.15 → maintien
check(
    "DNI 580 W/m² (zone hystérésis), maintien last=15%",
    calc_taux_dni(580, CIBLE, HYST, 0.15, True, 24.0, T_INT_HIGH),
    0.15
)

# Cas façade non exposée → 0% même si DNI fort
check(
    "DNI 800 W/m², façade non exposée → 0",
    calc_taux_dni(800, CIBLE, HYST, 0.0, False, 24.0, T_INT_HIGH),
    0.0
)

print("\n✅ Tous les checks passent.")
