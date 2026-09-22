from rich.console import Console
from rich.table import Table
from shared.contracts import StepStatus

console = Console()
STATUS_STYLE = {"VERIFIED": "bold green", "FAILED": "bold red", "BLOCKED": "bold yellow"}

def render_claim_vs_truth(results: dict):
    table = Table(title="CLAIM vs TRUTH")
    table.add_column("Step"); table.add_column("Agent Claims")
    table.add_column("System Truth"); table.add_column("Status")
    for step_id, r in results.items():
        truth = "matches" if r.status == StepStatus.VERIFIED else \
            f"MISMATCH -- {r.failure_class.value if r.failure_class else ''}"
        style = STATUS_STYLE.get(r.status.value, "white")
        row_style = "on red" if (r.status != StepStatus.VERIFIED
                                  and "success" in (r.claim or "").lower()) else None
        table.add_row(step_id, r.claim or "-", truth,
                      f"[{style}]{r.status.value}[/{style}]", style=row_style)
    console.print(table)

def render_final_banner(run_status):
    color = {"COMPLETE": "green", "PARTIAL": "yellow",
             "FAILED": "red", "ESCALATED": "magenta"}[run_status.value]
    console.rule(f"[bold {color}]FINAL STATUS: {run_status.value}[/bold {color}]")

def render_metrics_table(rows, naive_rate, veritas_rate):
    table = Table(title="False-Claim Rate: Naive vs VERITAS")
    table.add_column("Fault Mode"); table.add_column("Naive False Claim?")
    table.add_column("VERITAS False Claim?"); table.add_column("VERITAS Final Status")
    for r in rows:
        table.add_row(r["mode"], str(r["naive_false_claim"]),
                      str(r["veritas_false_claim"]), r["veritas_status"])
    console.print(table)
    console.print(f"[bold]Headline -- Naive: {naive_rate:.0%} false claims | "
                   f"VERITAS: {veritas_rate:.0%} false claims[/bold]")