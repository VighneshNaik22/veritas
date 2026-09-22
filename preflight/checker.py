def _no_delete_before_backup(plan):
    violations = []
    backup_seen = False
    for contract in plan:
        if contract.name.startswith("backup_"):
            backup_seen = True
        if contract.name.startswith("delete_") and not backup_seen:
            violations.append(
                f"Rule no_delete_before_backup violated by step '{contract.step_id}'."
            )
    return violations


def _every_step_has_expected(plan):
    return [
        f"Rule every_step_has_expected violated by step '{contract.step_id}'."
        for contract in plan
        if not contract.expected
    ]


def check_plan(plan: list) -> list[str]:
    return _no_delete_before_backup(plan) + _every_step_has_expected(plan)
