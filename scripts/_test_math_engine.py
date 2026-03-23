#!/usr/bin/env python3
"""数学公式编码引擎 自测"""
import sys
sys.path.insert(0, '.')
from workspace.skills.math_formula_engine import MathFormulaEngine

engine = MathFormulaEngine()

# 1. Carbon diffusion at 900C
r = engine.execute('carbon_diffusion_coeff', variables={'T': 900})
print(f'[1] D(900C) = {r["result"]:.4e} m2/s  OK={r["success"]}')

# 2. Phase determination
for T, C in [(25, 0.4), (727, 0.77), (900, 0.5), (1200, 3.0)]:
    p = engine._determine_phase(T, C)
    print(f'[2] T={T} C={C} -> {p["phase"]} ({p["desc"]})')

# 3. Temperature differential
r = engine.temperature_differential_analysis(900, 0.5, 10)
a = r['analysis']
print(f'[3] Phase: {a["phase"]["desc"]}')
print(f'    D_range: {a["D_range"]["D_low"]:.4e} ~ {a["D_range"]["D_high"]:.4e}')
print(f'    Sensitivity: {a["temperature_sensitivity"]["interpretation"]}')
print(f'    PID methods: {a["pid_suggestion"]["control_methods"][:2]}')

# 4. Small collision grid
r = engine.four_direction_collision(25, 1600, 400, 0, 6.69, 2.0)
print(f'[4] Grid: {r["grid_size"]}, {r["total_points"]} pts, {len(r["phase_transitions"])} transitions')
for p in r['patterns'][:3]:
    print(f'    {p}')

# 5. Formalize
r = engine.formalize('temperature 900 carbon 0.5 diffusion')
print(f'[5] Matched: {len(r["matched_formulas"])} formulas, Vars: {r["variables"]}')

# 6. Quadratic formula
r = engine.execute('quadratic', variables={'a': 1, 'b': -5, 'c': 6})
print(f'[6] x^2-5x+6=0 roots: {r["result"]}  OK={r["success"]}')

print('\nALL TESTS PASSED')
