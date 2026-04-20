from pydantic_ai import Agent, ModelMessage, SystemPromptPart, ModelRequest

summary_agent = Agent('groq:meta-llama/llama-4-scout-17b-16e-instruct', instructions="""
    Summarize this conversation, omitting small talk and unrelated topics.
    Focus on the technical discussion and next steps.
    """)

async def summarize_conversation(current_summary: str, messages: list[ModelMessage], latest = 5) -> list[ModelMessage]:
    if len(message) <= latest:
        return [], messages
    
    actual_latest = latest
    while actual_latest < len(message):
        first_recent_msg = messages[-actual_latest]
        
        has_tool_returns = False
        if isinstance(first_recent_msg, ModelRequest):
            has_tool_returns = any(isinstance(p, ToolReturnPart) for p in first_recent_msg.parts)
        
        if has_tool_returns:
            actual_latest += 1 #include tool call
        else:
            break

    recent_messages = messages[-actual_latest:]
    old_messages = messages[:-actual_latest]
    summary = await summary_agent.run(f"The current summary of the conversation is: {current_summary}\n\nThe messages need to be summarizedare: {old_messages}\n\nPlease provide an updated summary of the conversation based on the current summary and the new messages.")
    summary_message = [ModelRequest(
        parts=[
            SystemPromptPart(
                content=f"CONTEXT RECAP: The following is a summary of the earlier part of this conversation: {summary}"
            )
        ]
    )]
    return summary_message, recent_messages




