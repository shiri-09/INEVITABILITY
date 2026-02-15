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

def test_custom_analysis():
    url = 'http://localhost:8000/api/custom/run'
    body = json.dumps({
        'scenario_name': 'Test Custom Graph',
        'nodes': [
            {'id': 'attacker', 'type': 'identity', 'name': 'External Attacker'},
            {'id': 'firewall', 'type': 'control', 'name': 'Firewall', 'control_state': 'active', 'annual_cost': 50000},
            {'id': 'web', 'type': 'asset', 'name': 'Web Server'},
            {'id': 'ids', 'type': 'control', 'name': 'IDS', 'control_state': 'active', 'annual_cost': 35000},
            {'id': 'db', 'type': 'asset', 'name': 'Database', 'criticality': 'critical'},
        ],
        'edges': [
            {'source': 'attacker', 'target': 'web', 'edge_type': 'access', 'label': 'HTTP'},
            {'source': 'firewall', 'target': 'web', 'edge_type': 'control', 'label': 'Ingress filter'},
            {'source': 'web', 'target': 'db', 'edge_type': 'lateral', 'label': 'DB conn'},
            {'source': 'ids', 'target': 'web', 'edge_type': 'control', 'label': 'Monitor'},
        ],
        'goals': [
            {'name': 'Data Exfiltration', 'target_assets': ['db'], 'required_conditions': ['db']},
        ],
        'algorithm': 'greedy',
        'max_mcs_cardinality': 5,
    }).encode()
    req = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json'}, method='POST')
    r = urllib.request.urlopen(req)
    data = json.loads(r.read())
    
    aid = data['analysis_id'][:8]
    print(f"\n=== CUSTOM ANALYSIS TEST ===")
    print(f"Analysis ID: {aid}...")
    print(f"Scenario: {data.get('scenario_name', '?')}")
    print(f"Computation: {data['computation_time_ms']}ms")
    
    for i in data['inevitability_results']:
        print(f"  Goal: {i['goal_name']} | Score: {i['score']:.2f} | Inevitable: {i['is_inevitable']}")
    
    print(f"MCS sets: {len(data['mcs_results'])}")
    print(f"Theater reports: {len(data['theater_reports'])}")
    
    assert 'analysis_id' in data, "Missing analysis_id"
    assert len(data['inevitability_results']) > 0, "No inevitability results"
    assert len(data['mcs_results']) > 0, "No MCS results"
    assert len(data['theater_reports']) > 0, "No theater reports"
    
    return data

# Test all scenarios
for scenario in ['solarwinds', 'capital_one', 'enterprise_demo']:
    test_analysis(scenario)

# Test custom endpoint
test_custom_analysis()

print("\n=== ALL TESTS PASSED ===")
