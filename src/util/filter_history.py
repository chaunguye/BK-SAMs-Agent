from pydantic_ai import Agent, ModelMessage, SystemPromptPart, ModelRequest

summary_agent = Agent('groq:meta-llama/llama-4-scout-17b-16e-instruct', instructions="""
    Summarize this conversation, omitting small talk and unrelated topics.
    Focus on the technical discussion and next steps.
    """)

async def summarize_conversation(current_summary: str, messages: list[ModelMessage], latest = 5) -> list[ModelMessage]:
    recent_messages = messages[-latest:]
    old_messages = messages[:-latest]
    summary = await summary_agent.run(f"The current summary of the conversation is: {current_summary}\n\nThe messages need to be summarizedare: {old_messages}\n\nPlease provide an updated summary of the conversation based on the current summary and the new messages.")
    summary_message = [ModelRequest(
        parts=[
            SystemPromptPart(
                content=f"CONTEXT RECAP: The following is a summary of the earlier part of this conversation: {summary}"
            )
        ]
    )]
    return summary_message, recent_messages




