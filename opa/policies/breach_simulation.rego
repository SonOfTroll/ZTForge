package ztforge.breach_simulation

import rego.v1

# Rules used during breach simulation to evaluate if an attacker
# can traverse a given edge in the architecture graph.

default can_traverse := false

can_traverse if {
    input.edge.policy.action == "allow"
    credential_check
    device_check
    mfa_check
    time_check
    segment_check
}

# Credential check — attacker must have valid credentials
credential_check if {
    not input.edge.policy.conditions.require_valid_credential
}

credential_check if {
    input.edge.policy.conditions.require_valid_credential
    input.attacker.has_valid_credential == true
}

# Device compliance check
device_check if {
    not input.edge.policy.conditions.require_compliant_device
}

device_check if {
    input.edge.policy.conditions.require_compliant_device
    input.attacker.device_compliant == true
}

# MFA check
mfa_check if {
    not input.edge.policy.conditions.require_mfa
}

mfa_check if {
    input.edge.policy.conditions.require_mfa
    input.attacker.mfa_completed == true
}

# Time-based access control
time_check if {
    not input.edge.policy.conditions.allowed_hours
}

time_check if {
    input.edge.policy.conditions.allowed_hours
    not input.attacker.outside_business_hours
}

# Micro-segmentation enforcement
segment_check if {
    not input.edge.policy.conditions.enforce_microsegmentation
}

segment_check if {
    input.edge.policy.conditions.enforce_microsegmentation
    input.source_segment == input.target_segment
}

segment_check if {
    input.edge.policy.conditions.enforce_microsegmentation
    input.edge.policy.conditions.allow_cross_segment == true
}

# Risk scoring helper — used by the API but evaluated by OPA
risk_level := "critical" if { risk_score >= 80 }
risk_level := "high" if { risk_score >= 60; risk_score < 80 }
risk_level := "medium" if { risk_score >= 40; risk_score < 60 }
risk_level := "low" if { risk_score >= 20; risk_score < 40 }
risk_level := "minimal" if { risk_score < 20 }

risk_score := input.calculated_risk_score
