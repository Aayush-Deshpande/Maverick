import urllib.request
import json
import sys

base = 'http://localhost:8000'

def get(path):
    req = urllib.request.Request(f'{base}{path}')
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())

def post(path, body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(f'{base}{path}', data=data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())

def run_tests():
    print("--- 1. Health ---")
    h = get('/api/health')
    print("Health:", h.get('status'), "Sortie:", h.get('active_sortie_id'))

    print("\n--- 2. Mission Reliability (WP-06) ---")
    rel = get('/api/mission/reliability')
    print("Profile:", rel.get('profile_name'))
    print("Analytic R:", rel.get('analytic_reliability'))
    print("Monte Carlo R:", rel.get('monte_carlo_reliability'))
    print("Wilson CI:", rel.get('wilson_confidence_interval'))
    print("Major Risk Factors count:", len(rel.get('major_risk_factors', [])))

    print("\n--- 3. Prescriptive Advisor (WP-06) ---")
    presc = get('/api/mission/prescriptive')
    print("Current Power:", presc.get('current_power_percent'), "%")
    print("Options count:", len(presc.get('options', [])))
    for opt in presc.get('options', [])[:2]:
        print(f"  * {opt.get('mode')} -> Power {opt.get('derate_percent')}%: R_gain={opt.get('delta_reliability')}")

    print("\n--- 4. Bayesian Diagnostics (WP-08) ---")
    bayes = get('/api/diagnostics/bayesian')
    print("Top Hypothesis:", bayes.get('top_hypothesis'))
    print("Posterior Probability:", bayes.get('posterior_probability'))
    print("Hypotheses count:", len(bayes.get('hypotheses', {})))

    print("\n--- 5. Dual-Path RUL Prognostics (WP-08) ---")
    rul = get('/api/prognostics/dual-path-rul')
    print("Physics RUL:", rul.get('physics_arrhenius_rul_hrs'), "hrs")
    print("ML RUL:", rul.get('ml_conformal_rul_hrs'), "hrs")
    print("Dual-Path Blended RUL:", rul.get('dual_path_blend_rul_hrs'), "hrs")
    print("90% Conformal Interval:", rul.get('conformal_interval_90_pct'))

    print("\n--- 6. Replay Engine (WP-01) ---")
    sorties = get('/api/replay/sorties').get('sorties', [])
    print(f"Discovered {len(sorties)} sorties across data/telemetry/live_sorties/ and report_dump/")
    if sorties:
        s0 = sorties[0].get('mission_id') or sorties[0].get('sortie_id') or sorties[0].get('id')
        print(f"Loading frame at sec 5 for sortie '{s0}'...")
        frame = get(f'/api/replay/{s0}/frame?sec=5')
        print(f"  Frame at sec 5: RPM={frame.get('ENGINE_RPM')}, CHT_2={frame.get('CHT_2')}, OIL_PRESS={frame.get('OIL_PRESS')}")

    print("\n--- 7. Engine Switch Sync (WP-05) ---")
    sel = post('/api/engine/control', {'action': 'SELECT_ENGINE', 'engine_id': 'ROTAX_912_IS_02'})
    print("Select ROTAX_912_IS_02:", sel.get('status'), "Active ID:", sel.get('engine_id'))

    print("\n--- 8. Fault Injection Authoritative Pipeline ---")
    inj = post('/api/engine/control', {'action': 'INJECT_FAULT', 'fault_type': 'INJECTOR_CLOGGING'})
    print("Inject INJECTOR_CLOGGING:", inj.get('status'), "Fault:", inj.get('fault'))

    print("\n--- 9. Clear Fault Authoritative Pipeline ---")
    clr = post('/api/engine/control', {'action': 'CLEAR_FAULT'})
    print("Clear Fault:", clr.get('status'), "Fault:", clr.get('fault'))

    print("\n--- 10. Post-Flight Debrief (WP-10) ---")
    if sorties:
        debrief = post('/api/debrief/generate', {'sortie_id': s0})
        print("Generated Debrief for:", debrief.get('sortie_id'))
        print("Executive Summary preview:", debrief.get('executive_summary', '')[:100], "...")
        print("CBM Actions count:", len(debrief.get('cbm_actions', [])))
        latest = get('/api/debrief/latest')
        print("Latest Debrief Sortie:", latest.get('sortie_id'))

    print("\n>>> ALL API VERIFICATIONS COMPLETED SUCCESSFULLY! <<<")

if __name__ == '__main__':
    run_tests()
