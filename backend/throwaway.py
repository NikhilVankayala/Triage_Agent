from app.tools.index import resolve_action

# Approve the refund (row 2)
print("Approving 2:", resolve_action(2, "approve"))

# Reject the ticket (row 3)
print("Rejecting 3:", resolve_action(3, "reject"))

# Try to re-resolve an already-resolved one (should be guarded)
print("Re-approving 2:", resolve_action(2, "approve"))