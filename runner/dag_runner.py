# runner/dag_runner.py
from shared.contracts import StepStatus, StepResult, FailureClass

class DagRunner:
    def __init__(self, executor, verifier, classifier, recovery_engine):
        self.executor = executor
        self.verifier = verifier
        self.classifier = classifier
        self.recovery = recovery_engine

    def run(self, plan: list) -> dict:
        results: dict[str, StepResult] = {}
        for contract in plan:
            upstream_ok = all(
                results[d].status == StepStatus.VERIFIED
                for d in contract.depends_on
            )
            if not upstream_ok:
                results[contract.step_id] = StepResult(
                    step_id=contract.step_id, status=StepStatus.BLOCKED, claim="",
                )
                continue
            results[contract.step_id] = self._run_step(contract)
        return results

    def _run_step(self, contract) -> StepResult:
        attempts = 0
        while True:
            attempts += 1
            before = self.verifier.snapshot()
            tool_result = self.executor.execute(contract)
            evidence = self.verifier.verify(contract)
            collateral = self.verifier.collateral_detected(before, contract)
            failure_class = self.classifier(
                contract, evidence.details, evidence.passed,
                raised_timeout=tool_result.raised_timeout,
                collateral_detected=collateral,
            )
            passed = evidence.passed and not collateral

            if passed:
                return StepResult(contract.step_id, StepStatus.VERIFIED,
                                   tool_result.claim, evidence, FailureClass.NONE, attempts)

            decision = self.recovery.decide(contract, failure_class, attempts)
            if decision.action == "RETRY":
                continue
            if decision.action == "ESCALATE":
                return StepResult(contract.step_id, StepStatus.FAILED, tool_result.claim,
                                   evidence, failure_class, attempts, escalated=True)
            return StepResult(contract.step_id, StepStatus.FAILED, tool_result.claim,
                               evidence, failure_class, attempts)