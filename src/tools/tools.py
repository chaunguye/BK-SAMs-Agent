import json

from typing_extensions import Literal

from pydantic_ai import RunContext
import logfire
import os
from dataclasses import dataclass
from src.service.chunk_service import get_chunk_service
from src.service.activity_service import get_activity_service
from pydantic import Field
from datetime import datetime
import uuid
from src.util.chat_request import ActivityDetails
from src.agents.agent_config import AgentConfig

async def search_chunks(ctx: RunContext[AgentConfig],
                        query: str = Field (..., description="The student's query about activities or events. Extract the core technical query for searching relevant chunks in the database."),
                        top_k: int = Field(default=5, description="The number of top relevant chunks to return.")) -> str:
    """
    Search for relevant chunks in the database based on the query.
    """

    if ctx.deps and ctx.deps.chunk_service:
        chunk_service = ctx.deps.chunk_service
    else:
        chunk_service = get_chunk_service()
    with logfire.span("Searching Chunks with query: {}".format(query)):
        relevant_chunks = await chunk_service.search_chunk_by_query(query, top_k)
        logfire.info(f"Found {len(relevant_chunks)} relevant chunks: {relevant_chunks}")
    return 'Relevant chunks: ' + ','.join([chunk['text_content'] for chunk in relevant_chunks])


async def search_activity_chunks(ctx: RunContext[AgentConfig],
                        query: str = Field (..., description="The student's query about activities or events. Extract the core technical query for searching relevant chunks in the database."),
                        top_k: int = Field(default=5, description="The number of top relevant chunks to return."),
                        activity_id: uuid.UUID = Field(..., description="The ID of the activity for which to search chunks.")) -> str:
    """
    Search for relevant activity chunks in the database based on the query.
    """

    if ctx.deps and ctx.deps.chunk_service:
        chunk_service = ctx.deps.chunk_service
    else:
        chunk_service = get_chunk_service()
    with logfire.span("Searching Activity Chunks with query: {}".format(query)):
        relevant_chunks = await chunk_service.search_chunks_of_activity(query, top_k, activity_id)
        logfire.info(f"Found {len(relevant_chunks)} relevant activity chunks: {relevant_chunks}")
    for chunk in relevant_chunks:
        if 'id' in chunk:
            chunk['id'] = str(chunk['id'])
    return f"Relevant activity chunks: {json.dumps(relevant_chunks, default=str) if relevant_chunks else "No relevant activity chunks found based on the provided query and activity ID."}"

ActivityStatus = Literal['OPEN', 'CLOSED', 'COMPLETED', 'CANCELLED']
async def search_relevant_activities(ctx: RunContext[AgentConfig], 
                                    time_start: datetime = Field(default=None, description="The start time of the activity (format: YYYY-MM-DD)"),
                                    time_end: datetime = Field(default=None, description="The end time of the activity (format: YYYY-MM-DD)"),
                                    location: str = Field(default=None, description="The location of the activity"),
                                    status: ActivityStatus = Field(default=None, description="The status of the activity")) -> str:
    """
    Search for relevant activities based on activity name, time range, location, and status.
    """
    if ctx.deps and ctx.deps.activity_service:
        activity_service = ctx.deps.activity_service
    else:
        activity_service = get_activity_service()

    with logfire.span("Searching Relevant Activities with parameters: time_start={}, time_end={}, location={}, status={}".format(time_start, time_end, location, status)):
        relevant_activities = await activity_service.search_relevant_activity(time_start=time_start, time_end=time_end, location=location, status=status, top_k=5)
        logfire.info(f"Search parameters - time_start: {time_start}, time_end: {time_end}, location: {location}, status: {status}")
        logfire.info(f"Found {len(relevant_activities)} relevant activities: {relevant_activities}")
        if len(relevant_activities) == 0:
            return "No relevant activities found based on the provided parameters."
    return relevant_activities

async def get_activity_details(ctx: RunContext[AgentConfig], activity_id: uuid.UUID = Field(..., description="The ID of the activity to retrieve details for")) -> str:
    """
    Get the activity details based on the activity ID.
    """
    activity_details = await ctx.deps.activity_service.get_activity_details(activity_id)
    logfire.info(f"Getting details for activity_id: {activity_id}, Activity details: {activity_details}")
    serializable_details = dict(activity_details) if activity_details else None
    return json.dumps(serializable_details, default=str) if activity_details else "No activity found with the given ID."

async def register_activity(ctx: RunContext[AgentConfig], 
                            activity_details: ActivityDetails = Field(..., description="The details of the activity the student wants to register for, obtained from the tool search_activity_by_name")) -> str:
    """
    Register the student for the specified activity.
    Current logic:
    1. Check for activity_id in chat history (Case user ask for activity then register)
    2. If not found, search for activity_id based on activity_name, then register.
    """
    if not ctx.deps.student_id:
        return "Student ID is missing. Unable to register for the activity."
    with logfire.span("Registering for activity: {}".format(activity_details.id)):
        result = await ctx.deps.activity_service.register_activity(student_id=ctx.deps.student_id, activity_id=activity_details.id)
        logfire.info(f"Registering student_id: {ctx.deps.student_id} for activity: {activity_details.id} with result: {result}")
    return result

async def get_activity_ids_by_name(ctx: RunContext[AgentConfig], activity_name: str = Field(..., description="The name of the activity to search for its ID")) -> str:
    """
    Get the activity ID based on the activity name.
    """
    activity_service = get_activity_service()
    with logfire.span("Getting activity ID for activity name: {}".format(activity_name)):
        activity_details = await activity_service.search_activity_by_name(activity_name)
        logfire.info(f"Top Relevant Activities:{activity_details if activity_details else 'Not Found'}")
    
    for activity in activity_details:
        if 'id' in activity:
            activity['id'] = str(activity['id'])
    return json.dumps(activity_details, default=str) if activity_details else "No activity found with the given name."

async def unregister_activity(ctx: RunContext[AgentConfig], 
                              activity_id: uuid.UUID = Field(..., description="The ID of the activity the student wants to unregister from")) -> str:
    """
    Unregister the student from the specified activity.
    """
    if not ctx.deps.student_id:  
        return "Student ID is missing. Unable to unregister from the activity."
    with logfire.span("Unregistering from activity: {}".format(activity_id)):
        result = await ctx.deps.activity_service.unregister_activity(student_id=ctx.deps.student_id, activity_id=activity_id)
        logfire.info(f"Unregistering student_id: {ctx.deps.student_id} from activity: {activity_id} with result: {result}")
    return result

async def get_registered_activities(ctx: RunContext[AgentConfig]) -> str:
    """
    Get the list of activities the student is currently registered for.
    """
    if not ctx.deps.student_id:  
        return "Student ID is missing. Unable to retrieve registered activities."
    with logfire.span("Getting registered activities for student_id: {}".format(ctx.deps.student_id)):
        registered_activities = await ctx.deps.activity_service.get_registered_activities(student_id=ctx.deps.student_id)
        logfire.info(f"Registered activities for student_id: {ctx.deps.student_id}: {registered_activities}")
    
    serializable_activities = [dict(activity) for activity in registered_activities] if registered_activities else []
    for activity in serializable_activities:
        if 'id' in activity:
            activity['id'] = str(activity['id'])
    return json.dumps(serializable_activities, default=str) if registered_activities else "No registered activities found for the student."
