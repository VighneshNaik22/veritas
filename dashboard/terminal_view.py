from rich.console import Console
from rich.table import Table
from shared.contracts import StepStatus

console = Console()
STATUS_STYLE = {
    "VERIFIED": "bold green",
    "FAILED": "bold red",
    "BLOCKED": "bold yellow",
    "QUEUED (offline)": "bold cyan",
}

def render_claim_vs_truth(results: dict):
    table = Table(title="CLAIM vs TRUTH")
    table.add_column("Step"); table.add_column("Agent Claims")
    table.add_column("System Truth"); table.add_column("Status")
    for step_id, r in results.items():
        truth = "matches" if r.status == StepStatus.VERIFIED else \
            f"MISMATCH -- {r.failure_class.value if r.failure_class else ''}"
        queued = "queued_offline" in (r.claim or "").lower()
        style = STATUS_STYLE["QUEUED (offline)"] if queued else \
            STATUS_STYLE.get(r.status.value, "white")
        status_text = "QUEUED (offline)" if queued else r.status.value
        row_style = "on red" if (r.status != StepStatus.VERIFIED
                                  and "success" in (r.claim or "").lower()) else None
        table.add_row(step_id, r.claim or "-", truth,
                      f"[{style}]{status_text}[/{style}]", style=row_style)
    console.print(table)

def render_ledger_summary(ledger):
    count = ledger.conn.execute("SELECT COUNT(*) FROM evidence").fetchone()[0]
    integrity = all(
        status == "VERIFIED" for _, status in ledger.verify_chain()
    )
    label = "[bold green]VERIFIED[/bold green]" if integrity else \
        "[bold red]TAMPERED[/bold red]"
    console.print(f"Evidence records: {count} | Ledger: {label}")

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