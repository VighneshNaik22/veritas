from agent.tools import TOOL_REGISTRY

class Executor:
    def __init__(self, rw_conn, fault_injector):
        self.rw_conn = rw_conn
        self.fault_injector = fault_injector

    def execute(self, contract):
        tool_fn = TOOL_REGISTRY[contract.tool]
        return self.fault_injector.call(tool_fn, self.rw_conn, contract)