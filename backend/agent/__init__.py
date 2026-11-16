from backend import config


def run_agent(message: str, history: list | None = None) -> dict:
    """설정에 따라 Claude 또는 Mock Agent를 실행한다. 반환 형식은 동일."""
    if config.resolved_agent_mode() == "claude":
        from backend.agent.claude_agent import run_claude_agent
        return run_claude_agent(message, history)
    from backend.agent.mock_agent import run_mock_agent
    return run_mock_agent(message, history)
