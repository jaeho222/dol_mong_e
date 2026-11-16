"""Claude tool-use Agent.

흐름: 사용자 메시지 → Claude가 도구 선택 → 도구 실행 → 결과를 Claude에 돌려줌 → ... → 최종 답변
최대 AGENT_MAX_TURNS 번 반복. 마지막 rank_regions 결과는 프론트 카드 렌더링용으로 같이 반환.

TODO[AGENT]: 스트리밍 응답, 대화 히스토리 요약, 프롬프트 캐싱
"""
import json

import anthropic

from backend import config
from backend.agent.prompts import SYSTEM_PROMPT
from backend.tools.registry import TOOLS, TOOLS_BY_NAME


def run_claude_agent(message: str, history: list | None = None) -> dict:
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    messages = list(history or []) + [{"role": "user", "content": message}]
    tools = [t.to_anthropic() for t in TOOLS]
    trace, ranked = [], None

    for _ in range(config.AGENT_MAX_TURNS):
        resp = client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": resp.content})

        if resp.stop_reason != "tool_use":
            answer = "".join(b.text for b in resp.content if b.type == "text")
            return {"answer": answer, "ranked": ranked, "trace": trace, "mode": "claude"}

        tool_results = []
        for block in resp.content:
            if block.type != "tool_use":
                continue
            tool = TOOLS_BY_NAME.get(block.name)
            try:
                out = tool.run(block.input) if tool else {"error": f"unknown tool {block.name}"}
                is_error = False
            except Exception as e:  # 도구 에러는 Claude에게 돌려줘 스스로 고치게 한다
                out, is_error = {"error": str(e)}, True
            trace.append({"tool": block.name, "input": block.input, "error": is_error})
            if block.name == "rank_regions" and not is_error:
                ranked = out
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(out, ensure_ascii=False, default=str),
                "is_error": is_error,
            })
        messages.append({"role": "user", "content": tool_results})

    return {"answer": "조건이 복잡해서 계산을 끝내지 못했어요. 조금 더 간단히 말해 줄래요?",
            "ranked": ranked, "trace": trace, "mode": "claude"}
