"""
INEVITABILITY - Historical Breach Case Studies
Pre-built SCMs reconstructed from real-world breaches for demo and validation.
"""

from __future__ import annotations
from .models import (
    CausalGraph, InfraNode, InfraEdge, GoalPredicate, BreachCaseStudy, AttackStep,
    NodeType, EdgeType, EdgeConstraint, ConstraintType, ControlState,
    Criticality, GoalTemplate
)


def get_all_scenarios() -> dict[str, dict]:
    """Get all available demo scenarios."""
    return {
        "solarwinds": {
            "name": "SolarWinds Supply Chain Attack (2020)",
            "description": "Nation-state supply chain compromise → SAML forging → email exfiltration",
            "year": 2020,
            "expected_inev": 0.92,
        },
        "capital_one": {
            "name": "Capital One Data Breach (2019)",
            "description": "SSRF → IMDS → IAM role → S3 bucket exfiltration",
            "year": 2019,
            "expected_inev": 0.78,
        },
        "enterprise_demo": {
            "name": "Synthetic Enterprise Environment",
            "description": "Realistic enterprise with AD, cloud, and CI/CD — multiple attack goals",
            "year": 2024,
            "expected_inev": 0.65,
        },
        "okta": {
            "name": "Okta / Lapsus$ Breach (2022)",
            "description": "Third-party contractor compromise → customer tenant access → 366 orgs affected",
            "year": 2022,
            "expected_inev": 0.85,
        },
        "log4shell": {
            "name": "Log4Shell / CVE-2021-44228",
            "description": "JNDI injection → RCE → cloud credential theft → S3 exfiltration",
            "year": 2021,
            "expected_inev": 0.95,
        },
        "equifax": {
            "name": "Equifax Data Breach (2017)",
            "description": "Apache Struts CVE → web shell → plaintext creds → 148M records over 76 days",
            "year": 2017,
            "expected_inev": 0.97,
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
# SOLARWINDS 2020
# ═══════════════════════════════════════════════════════════════════════════════

def build_solarwinds() -> tuple[CausalGraph, list[GoalPredicate], BreachCaseStudy]:
    """Reconstruct the SolarWinds Sunburst supply chain attack (2020)."""

    nodes = [
        # Identities
        InfraNode(id="attacker", type=NodeType.IDENTITY, name="APT29 Attacker", description="Nation-state attacker (Russia SVR)", privilege_level="external"),
        InfraNode(id="dev_team", type=NodeType.IDENTITY, name="SolarWinds Dev Team", description="Build pipeline operators", privilege_level="internal", mfa_enabled=True),
        InfraNode(id="customer_admin", type=NodeType.IDENTITY, name="Customer Org Admin", description="Target org IT administrator", privilege_level="admin", mfa_enabled=True),

        # Build Pipeline
        InfraNode(id="build_server", type=NodeType.ASSET, name="SolarWinds Build Server", description="TeamCity CI/CD build system", criticality=Criticality.CRITICAL),
        InfraNode(id="orion_source", type=NodeType.ASSET, name="Orion Source Code", description="SolarWinds Orion platform source", criticality=Criticality.CRITICAL),
        InfraNode(id="signed_update", type=NodeType.ASSET, name="Signed Orion Update", description="Legitimately signed malicious DLL (SUNBURST)", criticality=Criticality.CRITICAL),

        # Customer Infrastructure
        InfraNode(id="orion_server", type=NodeType.ASSET, name="Customer Orion Server", description="Monitoring server running backdoored Orion", criticality=Criticality.HIGH),
        InfraNode(id="adfs_server", type=NodeType.ASSET, name="AD FS / SAML Server", description="Identity federation server", criticality=Criticality.CRITICAL),
        InfraNode(id="saml_token", type=NodeType.PRIVILEGE, name="Forged SAML Token", description="Golden SAML — forged authentication token"),
        InfraNode(id="o365_mailbox", type=NodeType.ASSET, name="O365 Executive Mailboxes", description="Target email data", criticality=Criticality.CRITICAL, data_classification=["confidential", "PII"]),

        # Controls (some theater, some real) — v2.0: effectiveness + bypass_probability
        InfraNode(id="ctrl_code_signing", type=NodeType.CONTROL, name="Code Signing", control_state=ControlState.ACTIVE, control_type="integrity", annual_cost=50000, description="Code signing for Orion builds", effectiveness=0.1, bypass_probability=0.9),
        InfraNode(id="ctrl_edr", type=NodeType.CONTROL, name="EDR (Endpoint Detection)", control_state=ControlState.ACTIVE, control_type="detection", annual_cost=180000, description="CrowdStrike/Carbon Black on endpoints", effectiveness=0.65, bypass_probability=0.35),
        InfraNode(id="ctrl_siem", type=NodeType.CONTROL, name="SIEM Monitoring", control_state=ControlState.ACTIVE, control_type="detection", annual_cost=220000, description="Splunk SIEM for log analysis", effectiveness=0.55, bypass_probability=0.45),
        InfraNode(id="ctrl_mfa", type=NodeType.CONTROL, name="MFA on Admin Accounts", control_state=ControlState.ACTIVE, control_type="authentication", annual_cost=15000, description="Multi-factor authentication", effectiveness=0.85, bypass_probability=0.15),
        InfraNode(id="ctrl_build_isolation", type=NodeType.CONTROL, name="Build Pipeline Isolation", control_state=ControlState.INACTIVE, control_type="segmentation", annual_cost=0, description="Isolated build environment", effectiveness=0.92, bypass_probability=0.08),
        InfraNode(id="ctrl_saml_monitoring", type=NodeType.CONTROL, name="SAML Token Audit", control_state=ControlState.INACTIVE, control_type="detection", annual_cost=0, description="Monitor for anomalous SAML assertions", effectiveness=0.88, bypass_probability=0.12),
        InfraNode(id="ctrl_network_seg", type=NodeType.CONTROL, name="Network Segmentation", control_state=ControlState.PARTIAL, control_type="segmentation", annual_cost=45000, description="VLAN segmentation — but monitoring tools are exempted", effectiveness=0.40, bypass_probability=0.60),
        InfraNode(id="ctrl_waf", type=NodeType.CONTROL, name="WAF", control_state=ControlState.ACTIVE, control_type="perimeter", annual_cost=35000, description="Web Application Firewall", effectiveness=0.70, bypass_probability=0.30),
    ]

    edges = [
        # Attack chain: APT29 → build server → malicious update — v2.0: exploit_probability
        InfraEdge(source="attacker", target="build_server", edge_type=EdgeType.ACCESS,
                  label="Compromise build pipeline via supply chain", exploit_probability=0.35,
                  constraint=EdgeConstraint(type=ConstraintType.CONDITIONAL, assumptions=["build_pipeline_accessible"])),
        InfraEdge(source="build_server", target="orion_source", edge_type=EdgeType.ACCESS,
                  label="Access to source code repository", exploit_probability=0.85),
        InfraEdge(source="orion_source", target="signed_update", edge_type=EdgeType.DEPENDENCY,
                  label="Inject SUNBURST backdoor into build", exploit_probability=0.75),

        InfraEdge(source="ctrl_code_signing", target="signed_update", edge_type=EdgeType.DEPENDENCY,
                  label="Signs the update (including malicious code)", exploit_probability=0.95),

        InfraEdge(source="ctrl_build_isolation", target="build_server", edge_type=EdgeType.CONTROL,
                  label="Would isolate build environment", exploit_probability=0.5),

        InfraEdge(source="signed_update", target="orion_server", edge_type=EdgeType.DEPENDENCY,
                  label="Customer installs signed update", exploit_probability=0.90),

        InfraEdge(source="orion_server", target="adfs_server", edge_type=EdgeType.LATERAL,
                  label="Orion monitoring agent has network access to ADFS", exploit_probability=0.65),

        InfraEdge(source="ctrl_network_seg", target="orion_server", edge_type=EdgeType.CONTROL,
                  label="Segmentation between monitoring and identity tiers", exploit_probability=0.5),

        InfraEdge(source="adfs_server", target="saml_token", edge_type=EdgeType.ESCALATION,
                  label="Extract SAML signing certificate → forge tokens", exploit_probability=0.70),

        InfraEdge(source="saml_token", target="o365_mailbox", edge_type=EdgeType.ACCESS,
                  label="Forged SAML token grants O365 access", exploit_probability=0.95),

        InfraEdge(source="ctrl_saml_monitoring", target="saml_token", edge_type=EdgeType.CONTROL,
                  label="Detect anomalous SAML assertions", exploit_probability=0.5),

        InfraEdge(source="ctrl_mfa", target="customer_admin", edge_type=EdgeType.CONTROL,
                  label="MFA on admin accounts", exploit_probability=0.5),
    ]

    graph = CausalGraph(
        nodes=nodes,
        edges=edges,
        metadata={
            "breach": "SolarWinds",
            "year": 2020,
            "reconstruction_sources": ["CISA", "Mandiant", "Senate testimony"],
        }
    )

    goals = [
        GoalPredicate(
            id="g_email_exfil",
            name="Executive Email Exfiltration",
            description="Exfiltrate executive O365 mailbox contents",
            template=GoalTemplate.DATA_EXFILTRATION,
            target_assets=["o365_mailbox"],
            required_conditions=["saml_token"],
            priority=Criticality.CRITICAL,
            threshold=0.7,
        ),
    ]

    case_study = BreachCaseStudy(
        breach_id="solarwinds_2020",
        name="SolarWinds SUNBURST",
        organization="SolarWinds / Multiple US Government Agencies",
        year=2020,
        timeline={
            "initial_compromise": "2019-10",
            "backdoor_deployed": "2020-03",
            "discovery": "2020-12-13",
            "dwell_time_days": 430,
        },
        attack_path=[
            AttackStep(step=1, technique="Supply Chain Compromise", technique_id="T1195.002", description="Inject SUNBURST into Orion build pipeline", domain="Build"),
            AttackStep(step=2, technique="Signed Malicious Update", technique_id="T1553.002", description="Legitimately signed DLL distributed via update", domain="Distribution"),
            AttackStep(step=3, technique="Backdoor Activation", technique_id="T1059", description="SUNBURST activates in customer environment", domain="Customer"),
            AttackStep(step=4, technique="Lateral Movement", technique_id="T1021", description="Move from Orion server to AD FS", domain="Customer"),
            AttackStep(step=5, technique="Golden SAML", technique_id="T1606.002", description="Forge SAML tokens using stolen signing cert", domain="Identity"),
            AttackStep(step=6, technique="Cloud Access", technique_id="T1078.004", description="Access O365 with forged SAML token", domain="Cloud"),
        ],
        impact={
            "organizations_affected": "18,000+ (update installed), ~100 (actively exploited)",
            "data_exfiltrated": "Government emails, security tools source code",
            "estimated_cost": "$100M+ (SolarWinds alone)",
        },
        headline="EDR, SIEM, and WAF were ALL security theater — the attack used a legitimately signed update",
        data_sources=["CISA Emergency Directive 21-01", "Mandiant UNC2452 Report", "US Senate Intelligence Hearing"],
    )

    return graph, goals, case_study


# ═══════════════════════════════════════════════════════════════════════════════
# CAPITAL ONE 2019
# ═══════════════════════════════════════════════════════════════════════════════

def build_capital_one() -> tuple[CausalGraph, list[GoalPredicate], BreachCaseStudy]:
    """Reconstruct the Capital One data breach (2019)."""

    nodes = [
        # Identities
        InfraNode(id="attacker_co", type=NodeType.IDENTITY, name="External Attacker", description="Paige Thompson (former AWS employee)", privilege_level="external"),

        # Infrastructure
        InfraNode(id="waf_proxy", type=NodeType.ASSET, name="ModSecurity WAF/Proxy", description="Reverse proxy with SSRF vulnerability", criticality=Criticality.HIGH),
        InfraNode(id="imds_v1", type=NodeType.ASSET, name="EC2 Instance Metadata (IMDSv1)", description="Instance metadata service v1 — no token required", criticality=Criticality.CRITICAL),
        InfraNode(id="iam_role", type=NodeType.PRIVILEGE, name="WAF IAM Role", description="Over-privileged IAM role attached to WAF EC2 instance"),
        InfraNode(id="s3_buckets", type=NodeType.ASSET, name="S3 Data Buckets", description="106M credit card records, SSNs", criticality=Criticality.CRITICAL, data_classification=["PII", "financial", "regulated"]),
        InfraNode(id="temp_creds", type=NodeType.PRIVILEGE, name="Temporary IAM Credentials", description="STS credentials from IMDS role"),

        # Controls — v2.0: effectiveness + bypass_probability
        InfraNode(id="ctrl_waf_co", type=NodeType.CONTROL, name="WAF Rules", control_state=ControlState.ACTIVE, control_type="perimeter", annual_cost=40000, effectiveness=0.30, bypass_probability=0.70),
        InfraNode(id="ctrl_imdsv2", type=NodeType.CONTROL, name="IMDSv2 Enforcement", control_state=ControlState.INACTIVE, control_type="configuration", annual_cost=0, description="Require IMDSv2 token for metadata access", effectiveness=0.95, bypass_probability=0.05),
        InfraNode(id="ctrl_iam_scope", type=NodeType.CONTROL, name="IAM Least Privilege", control_state=ControlState.INACTIVE, control_type="authorization", annual_cost=0, description="Scope IAM role to specific S3 prefixes", effectiveness=0.90, bypass_probability=0.10),
        InfraNode(id="ctrl_vpc_endpoint", type=NodeType.CONTROL, name="VPC Endpoint Policy", control_state=ControlState.INACTIVE, control_type="segmentation", annual_cost=0, description="Restrict S3 API calls via VPC endpoint", effectiveness=0.85, bypass_probability=0.15),
        InfraNode(id="ctrl_guardduty", type=NodeType.CONTROL, name="GuardDuty", control_state=ControlState.ACTIVE, control_type="detection", annual_cost=25000, description="AWS threat detection", effectiveness=0.50, bypass_probability=0.50),
        InfraNode(id="ctrl_cloudtrail", type=NodeType.CONTROL, name="CloudTrail Alerting", control_state=ControlState.ACTIVE, control_type="detection", annual_cost=15000, description="API call logging and alerting", effectiveness=0.45, bypass_probability=0.55),
        InfraNode(id="ctrl_encryption", type=NodeType.CONTROL, name="S3 Encryption (SSE-S3)", control_state=ControlState.ACTIVE, control_type="encryption", annual_cost=5000, description="Server-side encryption at rest", effectiveness=0.15, bypass_probability=0.85),
    ]

    edges = [
        # Attack chain — v2.0: exploit_probability
        InfraEdge(source="attacker_co", target="waf_proxy", edge_type=EdgeType.ACCESS,
                  label="SSRF via misconfigured WAF reverse proxy", exploit_probability=0.70,
                  constraint=EdgeConstraint(type=ConstraintType.CONDITIONAL, assumptions=["ssrf_vulnerability_exists"])),
        InfraEdge(source="waf_proxy", target="imds_v1", edge_type=EdgeType.ACCESS,
                  label="SSRF → request to 169.254.169.254 (IMDSv1)", exploit_probability=0.95),
        InfraEdge(source="imds_v1", target="temp_creds", edge_type=EdgeType.PRIVILEGE,
                  label="IMDSv1 returns IAM role credentials without token", exploit_probability=0.99),
        InfraEdge(source="temp_creds", target="iam_role", edge_type=EdgeType.PRIVILEGE,
                  label="Temporary credentials assume IAM role", exploit_probability=0.99),
        InfraEdge(source="iam_role", target="s3_buckets", edge_type=EdgeType.ACCESS,
                  label="Over-privileged role has s3:GetObject on all buckets", exploit_probability=0.95),

        # Controls
        InfraEdge(source="ctrl_imdsv2", target="imds_v1", edge_type=EdgeType.CONTROL,
                  label="IMDSv2 would require session token (blocks SSRF)", exploit_probability=0.5),
        InfraEdge(source="ctrl_iam_scope", target="iam_role", edge_type=EdgeType.CONTROL,
                  label="Least privilege would limit S3 access scope", exploit_probability=0.5),
        InfraEdge(source="ctrl_vpc_endpoint", target="s3_buckets", edge_type=EdgeType.CONTROL,
                  label="VPC endpoint policy restricts S3 API calls", exploit_probability=0.5),

        InfraEdge(source="ctrl_waf_co", target="waf_proxy", edge_type=EdgeType.DEPENDENCY,
                  label="WAF rules — but the attack used WAF as the SSRF pivot", exploit_probability=0.5),
    ]

    graph = CausalGraph(
        nodes=nodes,
        edges=edges,
        metadata={
            "breach": "Capital One",
            "year": 2019,
            "reconstruction_sources": ["SEC filing", "CISA advisory", "court documents"],
        }
    )

    goals = [
        GoalPredicate(
            id="g_data_exfil_co",
            name="S3 Data Exfiltration",
            description="Exfiltrate 106M credit card applications from S3",
            template=GoalTemplate.DATA_EXFILTRATION,
            target_assets=["s3_buckets"],
            required_conditions=["iam_role"],
            priority=Criticality.CRITICAL,
            threshold=0.7,
        ),
    ]

    case_study = BreachCaseStudy(
        breach_id="capital_one_2019",
        name="Capital One Data Breach",
        organization="Capital One Financial Corporation",
        year=2019,
        timeline={
            "initial_compromise": "2019-03-22",
            "data_exfiltration": "2019-03-22 to 2019-03-23",
            "discovery": "2019-07-17",
            "dwell_time_days": 117,
        },
        attack_path=[
            AttackStep(step=1, technique="SSRF", technique_id="T1190", description="Exploit SSRF in misconfigured WAF reverse proxy", domain="AWS"),
            AttackStep(step=2, technique="Cloud Instance Metadata", technique_id="T1552.005", description="Query IMDSv1 to obtain IAM role credentials", domain="AWS"),
            AttackStep(step=3, technique="Use Alternate Auth Material", technique_id="T1550", description="Use temporary STS credentials to assume IAM role", domain="AWS"),
            AttackStep(step=4, technique="Data from Cloud Storage", technique_id="T1530", description="List and download S3 bucket contents", domain="AWS"),
        ],
        impact={
            "records_exposed": "106 million credit card applications",
            "data_types": "SSNs, bank account numbers, credit scores, addresses",
            "fine": "$80 million (OCC consent order)",
            "settlement": "$190 million (class action)",
        },
        headline="SSRF → IMDSv1 → IAM → S3 was structurally inevitable. GuardDuty, CloudTrail, and encryption were theater.",
        data_sources=["SEC 8-K Filing", "CISA Advisory", "US District Court Western WA"],
    )

    return graph, goals, case_study


# ═══════════════════════════════════════════════════════════════════════════════
# SYNTHETIC ENTERPRISE
# ═══════════════════════════════════════════════════════════════════════════════

def build_enterprise_demo() -> tuple[CausalGraph, list[GoalPredicate], BreachCaseStudy]:
    """Build a synthetic enterprise environment with multiple attack goals."""

    nodes = [
        # Identities
        InfraNode(id="developer", type=NodeType.IDENTITY, name="Developer Account", description="Standard developer with Git and CI/CD access", privilege_level="user", mfa_enabled=True),
        InfraNode(id="it_admin", type=NodeType.IDENTITY, name="IT Administrator", description="Domain admin with broad access", privilege_level="admin", mfa_enabled=True),
        InfraNode(id="contractor", type=NodeType.IDENTITY, name="Contractor Account", description="Third-party contractor with VPN access", privilege_level="user", mfa_enabled=False),
        InfraNode(id="svc_account", type=NodeType.IDENTITY, name="Service Account (CI/CD)", description="Jenkins service account", privilege_level="service"),

        # Infrastructure
        InfraNode(id="vpn_gateway", type=NodeType.ASSET, name="VPN Gateway", description="Corporate VPN entry point", criticality=Criticality.HIGH),
        InfraNode(id="ad_dc", type=NodeType.ASSET, name="Active Directory DC", description="Primary domain controller", criticality=Criticality.CRITICAL),
        InfraNode(id="jenkins", type=NodeType.ASSET, name="Jenkins CI/CD", description="Build and deployment server", criticality=Criticality.HIGH),
        InfraNode(id="git_repo", type=NodeType.ASSET, name="Git Repository", description="Source code repository", criticality=Criticality.HIGH),
        InfraNode(id="prod_db", type=NodeType.ASSET, name="Production Database", description="PostgreSQL with customer PII", criticality=Criticality.CRITICAL, data_classification=["PII", "financial"]),
        InfraNode(id="prod_server", type=NodeType.ASSET, name="Production Server", description="Application server", criticality=Criticality.HIGH),
        InfraNode(id="backup_server", type=NodeType.ASSET, name="Backup Server", description="Veeam backup server", criticality=Criticality.HIGH),
        InfraNode(id="domain_admin_priv", type=NodeType.PRIVILEGE, name="Domain Admin Privilege", description="Full AD domain admin rights"),
        InfraNode(id="db_creds", type=NodeType.PRIVILEGE, name="Database Credentials", description="Production database connection strings in CI/CD"),

        # Controls — v2.0: effectiveness + bypass_probability
        InfraNode(id="ctrl_mfa_ent", type=NodeType.CONTROL, name="MFA Enforcement", control_state=ControlState.ACTIVE, control_type="authentication", annual_cost=12000, effectiveness=0.88, bypass_probability=0.12),
        InfraNode(id="ctrl_network_seg_ent", type=NodeType.CONTROL, name="Network Segmentation", control_state=ControlState.ACTIVE, control_type="segmentation", annual_cost=30000, effectiveness=0.75, bypass_probability=0.25),
        InfraNode(id="ctrl_pam", type=NodeType.CONTROL, name="Privileged Access Management", control_state=ControlState.INACTIVE, control_type="authorization", annual_cost=0, effectiveness=0.92, bypass_probability=0.08),
        InfraNode(id="ctrl_ci_isolation", type=NodeType.CONTROL, name="CI/CD Pipeline Isolation", control_state=ControlState.INACTIVE, control_type="segmentation", annual_cost=0, effectiveness=0.85, bypass_probability=0.15),
        InfraNode(id="ctrl_secret_mgmt", type=NodeType.CONTROL, name="Secrets Management (Vault)", control_state=ControlState.INACTIVE, control_type="credential", annual_cost=0, effectiveness=0.90, bypass_probability=0.10),
        InfraNode(id="ctrl_edr_ent", type=NodeType.CONTROL, name="EDR Solution", control_state=ControlState.ACTIVE, control_type="detection", annual_cost=95000, effectiveness=0.60, bypass_probability=0.40),
        InfraNode(id="ctrl_siem_ent", type=NodeType.CONTROL, name="SIEM/SOC", control_state=ControlState.ACTIVE, control_type="detection", annual_cost=150000, effectiveness=0.55, bypass_probability=0.45),
        InfraNode(id="ctrl_dlp", type=NodeType.CONTROL, name="DLP Agent", control_state=ControlState.ACTIVE, control_type="prevention", annual_cost=65000, effectiveness=0.50, bypass_probability=0.50),
        InfraNode(id="ctrl_backup_immutable", type=NodeType.CONTROL, name="Immutable Backups", control_state=ControlState.INACTIVE, control_type="resilience", annual_cost=0, effectiveness=0.95, bypass_probability=0.05),
        InfraNode(id="ctrl_waf_ent", type=NodeType.CONTROL, name="WAF", control_state=ControlState.ACTIVE, control_type="perimeter", annual_cost=28000, effectiveness=0.65, bypass_probability=0.35),
    ]

    edges = [
        # Contractor path — v2.0: exploit_probability
        InfraEdge(source="contractor", target="vpn_gateway", edge_type=EdgeType.ACCESS, label="VPN access without MFA", exploit_probability=0.80),
        InfraEdge(source="vpn_gateway", target="ad_dc", edge_type=EdgeType.LATERAL, label="Flat network — VPN subnet reaches DC", exploit_probability=0.70),
        InfraEdge(source="ad_dc", target="domain_admin_priv", edge_type=EdgeType.ESCALATION, label="Kerberoasting / DCSync", exploit_probability=0.55),

        # Developer path
        InfraEdge(source="developer", target="git_repo", edge_type=EdgeType.ACCESS, label="Git push access", exploit_probability=0.90),
        InfraEdge(source="git_repo", target="jenkins", edge_type=EdgeType.DEPENDENCY, label="Git push triggers CI/CD build", exploit_probability=0.95),
        InfraEdge(source="jenkins", target="db_creds", edge_type=EdgeType.PRIVILEGE, label="Jenkins has prod DB connection strings", exploit_probability=0.85),
        InfraEdge(source="db_creds", target="prod_db", edge_type=EdgeType.ACCESS, label="Database credentials grant full DB access", exploit_probability=0.95),
        InfraEdge(source="jenkins", target="prod_server", edge_type=EdgeType.ACCESS, label="Jenkins deploys to production", exploit_probability=0.90),

        # IT Admin path
        InfraEdge(source="it_admin", target="ad_dc", edge_type=EdgeType.ACCESS, label="Direct admin access to DC", exploit_probability=0.60),
        InfraEdge(source="domain_admin_priv", target="prod_server", edge_type=EdgeType.ACCESS, label="Domain admin reaches all servers", exploit_probability=0.95),
        InfraEdge(source="domain_admin_priv", target="backup_server", edge_type=EdgeType.ACCESS, label="Domain admin reaches backup", exploit_probability=0.90),
        InfraEdge(source="domain_admin_priv", target="prod_db", edge_type=EdgeType.ACCESS, label="Domain admin reaches database", exploit_probability=0.95),

        # Service account path
        InfraEdge(source="svc_account", target="jenkins", edge_type=EdgeType.ACCESS, label="Service account runs Jenkins", exploit_probability=0.75),

        # Controls
        InfraEdge(source="ctrl_mfa_ent", target="vpn_gateway", edge_type=EdgeType.CONTROL, label="MFA on VPN", exploit_probability=0.5),
        InfraEdge(source="ctrl_network_seg_ent", target="ad_dc", edge_type=EdgeType.CONTROL, label="Segment DC from general network", exploit_probability=0.5),
        InfraEdge(source="ctrl_pam", target="domain_admin_priv", edge_type=EdgeType.CONTROL, label="PAM controls domain admin usage", exploit_probability=0.5),
        InfraEdge(source="ctrl_ci_isolation", target="jenkins", edge_type=EdgeType.CONTROL, label="Isolate CI/CD from production network", exploit_probability=0.5),
        InfraEdge(source="ctrl_secret_mgmt", target="db_creds", edge_type=EdgeType.CONTROL, label="Vault rotates and restricts DB credentials", exploit_probability=0.5),
        InfraEdge(source="ctrl_backup_immutable", target="backup_server", edge_type=EdgeType.CONTROL, label="Immutable backups prevent encryption", exploit_probability=0.5),
    ]

    graph = CausalGraph(
        nodes=nodes,
        edges=edges,
        metadata={
            "environment": "Synthetic Enterprise",
            "total_identities": 4,
            "total_controls": 10,
            "critical_assets": 3,
        }
    )

    goals = [
        GoalPredicate(
            id="g_data_exfil_ent",
            name="Production Database Exfiltration",
            description="Exfiltrate customer PII from production database",
            template=GoalTemplate.DATA_EXFILTRATION,
            target_assets=["prod_db"],
            required_conditions=[],
            priority=Criticality.CRITICAL,
            threshold=0.7,
        ),
        GoalPredicate(
            id="g_domain_admin_ent",
            name="Domain Admin Compromise",
            description="Achieve domain admin privileges",
            template=GoalTemplate.DOMAIN_ADMIN,
            target_assets=["domain_admin_priv"],
            required_conditions=[],
            priority=Criticality.CRITICAL,
            threshold=0.7,
        ),
        GoalPredicate(
            id="g_ransomware_ent",
            name="Ransomware Deployment",
            description="Domain-wide ransomware deployment including backup encryption",
            template=GoalTemplate.RANSOMWARE,
            target_assets=["prod_server", "backup_server"],
            required_conditions=["domain_admin_priv"],
            priority=Criticality.CRITICAL,
            threshold=0.7,
        ),
    ]

    case_study = BreachCaseStudy(
        breach_id="enterprise_demo",
        name="Synthetic Enterprise Analysis",
        organization="Demo Corp",
        year=2024,
        attack_path=[
            AttackStep(step=1, technique="Initial Access", description="Compromise contractor account (no MFA)", domain="Identity"),
            AttackStep(step=2, technique="VPN Access", description="Connect to corporate VPN", domain="Network"),
            AttackStep(step=3, technique="Lateral Movement", description="Flat network → reach Domain Controller", domain="AD"),
            AttackStep(step=4, technique="Privilege Escalation", description="Kerberoasting → Domain Admin", domain="AD"),
            AttackStep(step=5, technique="Data Access", description="Domain Admin → production database", domain="Data"),
        ],
        headline="Contractor without MFA + flat network = structurally inevitable domain compromise",
        data_sources=["Synthetic — based on common enterprise patterns"],
    )

    return graph, goals, case_study


# ═══════════════════════════════════════════════════════════════════════════════
# OKTA / LAPSUS$ (2022)
# ═══════════════════════════════════════════════════════════════════════════════

def build_okta() -> tuple[CausalGraph, list[GoalPredicate], BreachCaseStudy]:
    """Okta / Lapsus$ breach — third-party contractor compromise → customer tenant access."""
    graph = CausalGraph(
        nodes=[
            # Attacker
            InfraNode(id="attacker_lapsus", type=NodeType.IDENTITY, name="Lapsus$ Group", description="Teenage threat actor group"),
            # Attack chain
            InfraNode(id="contractor_laptop", type=NodeType.ASSET, name="Sitel Contractor Laptop", description="Third-party support contractor workstation"),
            InfraNode(id="okta_superuser", type=NodeType.PRIVILEGE, name="Okta SuperUser Console", description="Internal customer support tool with tenant access"),
            InfraNode(id="customer_tenants", type=NodeType.ASSET, name="Customer Tenant Access", description="Ability to reset passwords and MFA for customer orgs"),
            InfraNode(id="customer_data", type=NodeType.ASSET, name="Customer Data Exposure", description="366 customer tenants potentially accessed"),
            # Controls
            InfraNode(id="ctrl_mfa_okta", type=NodeType.CONTROL, name="Contractor MFA", control_state=ControlState.PARTIAL, control_type="authentication", annual_cost=25000, description="MFA on contractor accounts — but contractor bypassed", effectiveness=0.60, bypass_probability=0.40),
            InfraNode(id="ctrl_pam_okta", type=NodeType.CONTROL, name="Privileged Access Management", control_state=ControlState.INACTIVE, control_type="pam", annual_cost=120000, description="PAM for superuser console — not enforced for contractors", effectiveness=0.90, bypass_probability=0.10),
            InfraNode(id="ctrl_soc_okta", type=NodeType.CONTROL, name="SOC Monitoring", control_state=ControlState.ACTIVE, control_type="monitoring", annual_cost=200000, description="Security Operations Center — detected but 2-month response delay", effectiveness=0.35, bypass_probability=0.65),
            InfraNode(id="ctrl_vendor_review", type=NodeType.CONTROL, name="Vendor Access Review", control_state=ControlState.INACTIVE, control_type="governance", annual_cost=50000, description="Quarterly vendor access reviews — not performed", effectiveness=0.75, bypass_probability=0.25),
        ],
        edges=[
            InfraEdge(source="attacker_lapsus", target="contractor_laptop", edge_type=EdgeType.ACCESS, label="Social engineering / credential purchase", exploit_probability=0.75),
            InfraEdge(source="contractor_laptop", target="okta_superuser", edge_type=EdgeType.ACCESS, label="RDP to internal support tools", exploit_probability=0.80),
            InfraEdge(source="okta_superuser", target="customer_tenants", edge_type=EdgeType.ESCALATION, label="SuperUser → tenant password/MFA reset", exploit_probability=0.90),
            InfraEdge(source="customer_tenants", target="customer_data", edge_type=EdgeType.ACCESS, label="Tenant access → customer data", exploit_probability=0.95),
            # Controls
            InfraEdge(source="ctrl_mfa_okta", target="contractor_laptop", edge_type=EdgeType.CONTROL, label="MFA should block contractor access", exploit_probability=0.5),
            InfraEdge(source="ctrl_pam_okta", target="okta_superuser", edge_type=EdgeType.CONTROL, label="PAM should gate superuser access", exploit_probability=0.5),
            InfraEdge(source="ctrl_soc_okta", target="customer_tenants", edge_type=EdgeType.CONTROL, label="SOC should detect lateral access to tenants", exploit_probability=0.5),
            InfraEdge(source="ctrl_vendor_review", target="contractor_laptop", edge_type=EdgeType.CONTROL, label="Vendor access review should limit contractor scope", exploit_probability=0.5),
        ],
    )

    goals = [
        GoalPredicate(
            id="g_okta_tenant_access",
            name="Customer Tenant Compromise",
            description="Access to Okta customer tenant administration",
            template=GoalTemplate.DATA_EXFILTRATION,
            target_assets=["customer_data"],
            required_conditions=[],
            priority=Criticality.CRITICAL,
            threshold=0.7,
        ),
    ]

    case_study = BreachCaseStudy(
        breach_id="okta",
        name="Okta / Lapsus$ Breach",
        organization="Okta",
        year=2022,
        attack_path=[
            AttackStep(step=1, technique="Social Engineering", description="Purchased contractor credentials from underground market", domain="Identity"),
            AttackStep(step=2, technique="Contractor Access", description="RDP into Sitel contractor workstation", domain="Network"),
            AttackStep(step=3, technique="Privilege Abuse", description="Access Okta SuperUser console via contractor privileges", domain="Application"),
            AttackStep(step=4, technique="Customer Impact", description="Reset passwords/MFA for 366 customer tenants", domain="Data"),
        ],
        headline="Third-party contractor with excessive privileges = 366 customer tenants compromised",
        data_sources=["Okta disclosure (March 2022)", "Lapsus$ Telegram posts"],
    )

    return graph, goals, case_study


# ═══════════════════════════════════════════════════════════════════════════════
# LOG4SHELL (2021)
# ═══════════════════════════════════════════════════════════════════════════════

def build_log4shell() -> tuple[CausalGraph, list[GoalPredicate], BreachCaseStudy]:
    """Log4Shell (CVE-2021-44228) — RCE through logging → lateral movement → cloud takeover."""
    graph = CausalGraph(
        nodes=[
            # Attacker
            InfraNode(id="attacker_log4j", type=NodeType.IDENTITY, name="Remote Attacker", description="Internet-based attacker exploiting Log4j"),
            # Attack chain
            InfraNode(id="web_app", type=NodeType.ASSET, name="Java Web Application", description="Public-facing application using Log4j for logging"),
            InfraNode(id="jndi_rce", type=NodeType.ASSET, name="JNDI RCE Execution", description="Remote code execution via JNDI lookup injection"),
            InfraNode(id="app_server", type=NodeType.ASSET, name="Application Server", description="Internal server running the vulnerable application"),
            InfraNode(id="cloud_creds", type=NodeType.PRIVILEGE, name="Cloud IAM Credentials", description="AWS credentials from instance metadata or env vars"),
            InfraNode(id="s3_data", type=NodeType.ASSET, name="S3 Data Buckets", description="Sensitive data in S3 buckets accessible via stolen creds"),
            InfraNode(id="k8s_cluster", type=NodeType.ASSET, name="Kubernetes Cluster", description="Container orchestration cluster"),
            # Controls
            InfraNode(id="ctrl_waf_log4j", type=NodeType.CONTROL, name="WAF Rules", control_state=ControlState.PARTIAL, control_type="waf", annual_cost=40000, description="WAF blocking JNDI patterns — but obfuscation bypasses exist", effectiveness=0.40, bypass_probability=0.60),
            InfraNode(id="ctrl_imds_v2", type=NodeType.CONTROL, name="IMDSv2 Enforcement", control_state=ControlState.INACTIVE, control_type="cloud_config", annual_cost=0, description="Instance Metadata Service v2 — not enforced (free to enable!)", effectiveness=0.95, bypass_probability=0.05),
            InfraNode(id="ctrl_iam_scope", type=NodeType.CONTROL, name="IAM Least Privilege", control_state=ControlState.INACTIVE, control_type="iam", annual_cost=30000, description="IAM role scoping — app role has S3:* and K8s admin", effectiveness=0.88, bypass_probability=0.12),
            InfraNode(id="ctrl_patch", type=NodeType.CONTROL, name="Patch Management", control_state=ControlState.INACTIVE, control_type="vulnerability", annual_cost=60000, description="Log4j patch — not applied within 72 hours of CVE disclosure", effectiveness=0.98, bypass_probability=0.02),
            InfraNode(id="ctrl_egress", type=NodeType.CONTROL, name="Egress Filtering", control_state=ControlState.INACTIVE, control_type="network", annual_cost=15000, description="Outbound LDAP/RMI filtering — not implemented", effectiveness=0.85, bypass_probability=0.15),
        ],
        edges=[
            InfraEdge(source="attacker_log4j", target="web_app", edge_type=EdgeType.ACCESS, label="Crafted HTTP request with JNDI payload", exploit_probability=0.85),
            InfraEdge(source="web_app", target="jndi_rce", edge_type=EdgeType.ACCESS, label="Log4j processes malicious JNDI lookup", exploit_probability=0.90),
            InfraEdge(source="jndi_rce", target="app_server", edge_type=EdgeType.ACCESS, label="JNDI callback → arbitrary code execution", exploit_probability=0.80),
            InfraEdge(source="app_server", target="cloud_creds", edge_type=EdgeType.ESCALATION, label="Instance metadata / env vars → cloud creds", exploit_probability=0.75),
            InfraEdge(source="cloud_creds", target="s3_data", edge_type=EdgeType.ACCESS, label="Stolen IAM creds → S3 bucket access", exploit_probability=0.90),
            InfraEdge(source="cloud_creds", target="k8s_cluster", edge_type=EdgeType.ACCESS, label="Stolen IAM creds → K8s cluster admin", exploit_probability=0.85),
            # Controls
            InfraEdge(source="ctrl_waf_log4j", target="web_app", edge_type=EdgeType.CONTROL, label="WAF pattern matching for JNDI strings", exploit_probability=0.5),
            InfraEdge(source="ctrl_imds_v2", target="cloud_creds", edge_type=EdgeType.CONTROL, label="IMDSv2 blocks unauthenticated metadata access", exploit_probability=0.5),
            InfraEdge(source="ctrl_iam_scope", target="s3_data", edge_type=EdgeType.CONTROL, label="Least privilege limits blast radius", exploit_probability=0.5),
            InfraEdge(source="ctrl_patch", target="jndi_rce", edge_type=EdgeType.CONTROL, label="Patching Log4j removes JNDI vulnerability", exploit_probability=0.5),
            InfraEdge(source="ctrl_egress", target="jndi_rce", edge_type=EdgeType.CONTROL, label="Egress filtering blocks JNDI callback", exploit_probability=0.5),
        ],
    )

    goals = [
        GoalPredicate(
            id="g_log4j_s3_exfil",
            name="S3 Data Exfiltration",
            description="Exfiltrate sensitive data from S3 via Log4Shell",
            template=GoalTemplate.DATA_EXFILTRATION,
            target_assets=["s3_data"],
            required_conditions=[],
            priority=Criticality.CRITICAL,
            threshold=0.7,
        ),
        GoalPredicate(
            id="g_log4j_k8s_takeover",
            name="Kubernetes Cluster Takeover",
            description="Gain admin access to Kubernetes cluster",
            template=GoalTemplate.DOMAIN_ADMIN,
            target_assets=["k8s_cluster"],
            required_conditions=[],
            priority=Criticality.HIGH,
            threshold=0.7,
        ),
    ]

    case_study = BreachCaseStudy(
        breach_id="log4shell",
        name="Log4Shell (CVE-2021-44228)",
        organization="Generic Enterprise",
        year=2021,
        attack_path=[
            AttackStep(step=1, technique="Initial Access", description="Crafted JNDI payload in HTTP request header", domain="Application"),
            AttackStep(step=2, technique="RCE", description="Log4j processes JNDI lookup → remote code execution", domain="Application"),
            AttackStep(step=3, technique="Credential Theft", description="Instance metadata → AWS IAM credentials", domain="Cloud"),
            AttackStep(step=4, technique="Data Exfiltration", description="IAM creds → S3 bucket access + K8s admin", domain="Cloud"),
        ],
        headline="Unpatched Log4j + overprivileged IAM + no IMDSv2 = inevitable cloud compromise from a single HTTP request",
        data_sources=["CVE-2021-44228", "CISA advisory", "Multiple incident reports"],
    )

    return graph, goals, case_study


# ═══════════════════════════════════════════════════════════════════════════════
# EQUIFAX (2017)
# ═══════════════════════════════════════════════════════════════════════════════

def build_equifax() -> tuple[CausalGraph, list[GoalPredicate], BreachCaseStudy]:
    """Equifax breach — Apache Struts CVE → 147M records exfiltrated."""
    graph = CausalGraph(
        nodes=[
            InfraNode(id="attacker_eq", type=NodeType.IDENTITY, name="Attacker", description="Nation-state attacker exploiting Apache Struts"),
            InfraNode(id="struts_portal", type=NodeType.ASSET, name="Consumer Portal", description="Public-facing dispute portal running Apache Struts"),
            InfraNode(id="webshell", type=NodeType.ASSET, name="Web Shell", description="Persistent backdoor on portal server"),
            InfraNode(id="internal_db_creds", type=NodeType.PRIVILEGE, name="Database Credentials", description="Unencrypted DB credentials in config files"),
            InfraNode(id="pii_database", type=NodeType.ASSET, name="PII Database", description="148M consumer records (SSN, DOB, addresses)"),
            InfraNode(id="exfil_staging", type=NodeType.ASSET, name="Data Exfiltration", description="Staged and exfiltrated data over 76 days"),
            # Controls
            InfraNode(id="ctrl_patch_eq", type=NodeType.CONTROL, name="Patch Management", control_state=ControlState.INACTIVE, control_type="vulnerability", annual_cost=80000, description="Apache Struts patch — CVE published March, exploited May, 2 months unpatched", effectiveness=0.97, bypass_probability=0.03),
            InfraNode(id="ctrl_ssl_inspect", type=NodeType.CONTROL, name="SSL Inspection", control_state=ControlState.INACTIVE, control_type="monitoring", annual_cost=90000, description="SSL/TLS inspection on egress — certificate expired, inspection disabled 19 months", effectiveness=0.80, bypass_probability=0.20),
            InfraNode(id="ctrl_db_encrypt", type=NodeType.CONTROL, name="Database Encryption", control_state=ControlState.INACTIVE, control_type="encryption", annual_cost=50000, description="Encryption at rest — PII stored in plaintext", effectiveness=0.75, bypass_probability=0.25),
            InfraNode(id="ctrl_segmentation_eq", type=NodeType.CONTROL, name="Network Segmentation", control_state=ControlState.INACTIVE, control_type="segmentation", annual_cost=100000, description="Segment public web from internal DBs — flat network", effectiveness=0.85, bypass_probability=0.15),
            InfraNode(id="ctrl_ids_eq", type=NodeType.CONTROL, name="IDS/IPS", control_state=ControlState.ACTIVE, control_type="monitoring", annual_cost=150000, description="Intrusion detection — present but SSL cert expired broke inspection", effectiveness=0.25, bypass_probability=0.75),
        ],
        edges=[
            InfraEdge(source="attacker_eq", target="struts_portal", edge_type=EdgeType.ACCESS, label="Exploit CVE-2017-5638 in Apache Struts", exploit_probability=0.85),
            InfraEdge(source="struts_portal", target="webshell", edge_type=EdgeType.ACCESS, label="Deploy web shell on compromised server", exploit_probability=0.80),
            InfraEdge(source="webshell", target="internal_db_creds", edge_type=EdgeType.ACCESS, label="Harvest plaintext DB credentials from config", exploit_probability=0.90),
            InfraEdge(source="internal_db_creds", target="pii_database", edge_type=EdgeType.ACCESS, label="Connect to databases with harvested credentials", exploit_probability=0.95),
            InfraEdge(source="pii_database", target="exfil_staging", edge_type=EdgeType.ACCESS, label="Stage and exfiltrate 148M records over 76 days", exploit_probability=0.85),
            # Controls
            InfraEdge(source="ctrl_patch_eq", target="struts_portal", edge_type=EdgeType.CONTROL, label="Patching Struts blocks initial exploit", exploit_probability=0.5),
            InfraEdge(source="ctrl_ssl_inspect", target="exfil_staging", edge_type=EdgeType.CONTROL, label="SSL inspection detects exfiltration traffic", exploit_probability=0.5),
            InfraEdge(source="ctrl_db_encrypt", target="pii_database", edge_type=EdgeType.CONTROL, label="Encryption renders stolen data useless", exploit_probability=0.5),
            InfraEdge(source="ctrl_segmentation_eq", target="internal_db_creds", edge_type=EdgeType.CONTROL, label="Segmentation blocks web→DB lateral movement", exploit_probability=0.5),
            InfraEdge(source="ctrl_ids_eq", target="webshell", edge_type=EdgeType.CONTROL, label="IDS should detect web shell installation", exploit_probability=0.5),
        ],
    )

    goals = [
        GoalPredicate(
            id="g_equifax_exfil",
            name="Mass PII Exfiltration",
            description="Exfiltrate 148 million consumer records",
            template=GoalTemplate.DATA_EXFILTRATION,
            target_assets=["exfil_staging"],
            required_conditions=[],
            priority=Criticality.CRITICAL,
            threshold=0.7,
        ),
    ]

    case_study = BreachCaseStudy(
        breach_id="equifax",
        name="Equifax Data Breach",
        organization="Equifax",
        year=2017,
        attack_path=[
            AttackStep(step=1, technique="Initial Exploit", description="CVE-2017-5638 Apache Struts RCE on consumer portal", domain="Application"),
            AttackStep(step=2, technique="Persistence", description="Web shell deployed for persistent access", domain="Server"),
            AttackStep(step=3, technique="Credential Harvest", description="Plaintext database credentials from config files", domain="Data"),
            AttackStep(step=4, technique="Data Access", description="Direct database queries to PII tables", domain="Database"),
            AttackStep(step=5, technique="Exfiltration", description="76-day exfiltration of 148M records undetected", domain="Network"),
        ],
        headline="Unpatched Struts + flat network + plaintext creds + expired SSL cert = 148M records stolen over 76 days",
        data_sources=["US House Committee report", "GAO-18-559", "Equifax SEC filing"],
    )

    return graph, goals, case_study


# ═══════════════════════════════════════════════════════════════════════════════
# LOADER
# ═══════════════════════════════════════════════════════════════════════════════

def load_scenario(scenario_id: str) -> tuple[CausalGraph, list[GoalPredicate], BreachCaseStudy]:
    """Load a pre-built scenario by ID."""
    builders = {
        "solarwinds": build_solarwinds,
        "capital_one": build_capital_one,
        "enterprise_demo": build_enterprise_demo,
        "okta": build_okta,
        "log4shell": build_log4shell,
        "equifax": build_equifax,
    }

    builder = builders.get(scenario_id)
    if not builder:
        raise ValueError(f"Unknown scenario: {scenario_id}. Available: {list(builders.keys())}")

    return builder()
