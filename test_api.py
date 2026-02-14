"""Quick test script for the INEVITABILITY API."""
import urllib.request
import json

def test_analysis(scenario_id):
    url = f'http://localhost:8000/api/demo/run/{scenario_id}'
    body = json.dumps({
        'scenario_id': scenario_id,
        'algorithm': 'greedy',
        'max_mcs_cardinality': 5,
    }).encode()
    req = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json'}, method='POST')
    r = urllib.request.urlopen(req)
    data = json.loads(r.read())
    
    aid = data['analysis_id'][:8]
    print(f"\n=== {scenario_id.upper()} ANALYSIS ===")
    print(f"Analysis ID: {aid}...")
    print(f"Computation: {data['computation_time_ms']}ms")
    
    for i in data['inevitability_results']:
        print(f"  Goal: {i['goal_name']} | Score: {i['score']:.2f} | Inevitable: {i['is_inevitable']}")
    
    print(f"MCS sets: {len(data['mcs_results'])}")
    print(f"Theater reports: {len(data['theater_reports'])}")
    print(f"Collapse frames: {len(data['collapse_frames'])}")
    
    econ = data.get('economic_report', {})
    print(f"Total spend: ${econ.get('total_security_spend', 0):,.0f}")
    print(f"Wasted: ${econ.get('wasted_spend', 0):,.0f}")
    wr = econ.get('waste_ratio', 0)
    print(f"Waste ratio: {wr*100:.1f}%")
    
    frag = data.get('fragility_profile', {})
    print(f"Fragility grade: {frag.get('grade', '?')}")
    
    return data

# Test all scenarios
for scenario in ['solarwinds', 'capital_one', 'enterprise_demo']:
    test_analysis(scenario)

print("\n=== ALL TESTS PASSED ===")
