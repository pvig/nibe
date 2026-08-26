#!/usr/bin/env python3
"""
Self-check minimal pour la dérivée et sa transformation quadratique (vitesse^2).
"""

def calc_anticipation(samples):
    recent_samples = samples[-3:]
    if len(recent_samples) >= 2:
        dt_h = (recent_samples[-1]["timestamp"] - recent_samples[0]["timestamp"]) / 3600.0
        d_text_dt = (recent_samples[-1]["t_ext"] - recent_samples[0]["t_ext"]) / dt_h if dt_h > 0 else 0.0
    else:
        d_text_dt = 0.0

    v_pos = max(0.0, d_text_dt)
    return d_text_dt, v_pos ** 2

# 1. Faible hausse (0.4°C/h) -> quasi nul (+0.16°C)
_, boost_faible = calc_anticipation([
    {"timestamp": 1000, "t_ext": 20.0},
    {"timestamp": 1450, "t_ext": 20.05},
    {"timestamp": 1900, "t_ext": 20.10},  # +0.1°C en 900s (15m) => 0.4°C/h
])
assert round(boost_faible, 2) == 0.16, f"Obtenu {boost_faible}"

# 2. Hausse modérée (1.0°C/h) -> +1.0°C
_, boost_modere = calc_anticipation([
    {"timestamp": 1000, "t_ext": 20.0},
    {"timestamp": 1450, "t_ext": 20.125},
    {"timestamp": 1900, "t_ext": 20.25},  # +0.25°C en 15m => 1.0°C/h
])
assert round(boost_modere, 2) == 1.0, f"Obtenu {boost_modere}"

# 3. Hausse rapide (2.0°C/h) -> fort boost (+4.0°C)
_, boost_fort = calc_anticipation([
    {"timestamp": 1000, "t_ext": 20.0},
    {"timestamp": 1450, "t_ext": 20.25},
    {"timestamp": 1900, "t_ext": 20.50},  # +0.5°C en 15m => 2.0°C/h
])
assert round(boost_fort, 2) == 4.0, f"Obtenu {boost_fort}"

print("✅ Checks transformation quadratique (vitesse^2) validés.")
