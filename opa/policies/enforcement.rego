package ztforge.enforcement

import rego.v1

# Runtime enforcement rules — used by the enforcement sidecar to
# make real-time access decisions based on canvas-defined policies.

default allow := false

# Check against canvas-defined access policies
allow if {
    canvas := data.ztforge.canvases[input.canvas_id]
    edge := canvas.edges[_]
    edge.source == input.source
    edge.target == input.target
    edge.policy.action == "allow"
    meets_conditions(edge.policy.conditions, input)
}

meets_conditions(conditions, req) if {
    mfa_ok(conditions, req)
    device_ok(conditions, req)
    credential_ok(conditions, req)
}

mfa_ok(conditions, req) if { not conditions.require_mfa }
mfa_ok(conditions, req) if { conditions.require_mfa; req.user.mfa_completed == true }

device_ok(conditions, req) if { not conditions.require_compliant_device }
device_ok(conditions, req) if { conditions.require_compliant_device; req.user.device_compliant == true }

credential_ok(conditions, req) if { not conditions.require_valid_credential }
credential_ok(conditions, req) if { conditions.require_valid_credential; req.user.authenticated == true }

# Decision reason for audit logging
reason := "allowed: all policy conditions met" if { allow }
reason := "denied: no matching allow policy" if { not allow }
