# Function: build_qdrant_security_filter(user) -> Filter
# - Create "must" conditions list:
#   - Condition 1: tenant_id field must exactly match user.tenant_id
#   - Condition 2: roles_allowed field must match ANY of [user.role] (user's role must be in document's allowed roles)
# - Create "must_not" conditions list (initially empty):
# - If user.role is NOT "admin":
#   - Add condition: sensitive field must NOT be True (non-admins can't see sensitive docs)
# - Return Filter object with:
#   - must = must_conditions list
#   - must_not = must_not_conditions list