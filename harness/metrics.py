FAULT_MODES = ["GHOST_SUCCESS", "TIMEOUT_THEN_RECOVER", "WRONG_VALUE", "COLLATERAL"]

def run_comparison(build_fresh_world, run_naive, run_veritas):
    rows = []
    for mode in ["CLEAN"] + FAULT_MODES:
        fault_map = {} if mode == "CLEAN" else {"step_2": mode}

        build_fresh_world()
        naive_status, naive_truth = run_naive(fault_map)

        build_fresh_world()
        veritas_status, veritas_truth = run_veritas(fault_map)

        rows.append({
            "mode": mode,
            "naive_false_claim": (naive_status.value == "COMPLETE") and not naive_truth,
            "veritas_false_claim": (veritas_status.value == "COMPLETE") and not veritas_truth,
            "veritas_status": veritas_status.value,
        })

    naive_rate = sum(r["naive_false_claim"] for r in rows) / len(rows)
    veritas_rate = sum(r["veritas_false_claim"] for r in rows) / len(rows)
    return rows, naive_rate, veritas_rate