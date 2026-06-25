package ztforge.base

import rego.v1

# Default deny — the foundation of Zero Trust.
# Every access must be explicitly allowed by a policy.
default allow := false

# Base ZT tenets (NIST 800-207):
# 1. All resources require authenticated access
# 2. Access is granted on a per-session basis
# 3. Access is determined by dynamic policy

allow if {
    input.authenticated == true
    input.session_valid == true
    valid_role
}

valid_role if {
    input.role in {"admin", "editor", "viewer"}
}

# Deny expired sessions regardless of other policies
deny_reason contains "session_expired" if {
    input.session_valid == false
}

deny_reason contains "unauthenticated" if {
    input.authenticated == false
}
