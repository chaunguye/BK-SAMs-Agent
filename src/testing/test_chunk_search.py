import pytest
import pytest_asyncio
import uuid
import json
import os
import src.database.database_connect as db_mod
import src.repository.chunk_repo as chunk_repo_mod
import src.service.chunk_service as chunk_service_mod
from src.service.chunk_service import get_chunk_service

# Define 10 test scenarios for search_chunks_of_activity
# Activity IDs and expected Chunk IDs are based on the JSON tables
scenarios = [
    {
        "query": "Trận chung kết giữa khoa nào", 
        "activity_id": "81df543a-717e-4092-8378-b753d386f1f1", 
        "expected_chunk_id": "c85047ed-ce31-4bd3-92f7-bd793f5de03f"
    },
    {
        "query": "Dụng cụ cổ vũ được cung cấp", 
        "activity_id": "81df543a-717e-4092-8378-b753d386f1f1", 
        "expected_chunk_id": "025fe47c-e35c-4c08-ab38-2bc8b9fe76d1"
    },
    {
        "query": "Kịch bản cổ động khi đội nhà ghi điểm", 
        "activity_id": "81df543a-717e-4092-8378-b753d386f1f1", 
        "expected_chunk_id": "3f06c556-2b6f-43e9-9811-43de80ba6fab"
    },
    {
        "query": "Điểm rèn luyện được nhận", 
        "activity_id": "81df543a-717e-4092-8378-b753d386f1f1", 
        "expected_chunk_id": "83b373c6-3e00-4b83-90f0-4a3125eaec11"
    },
    {
        "query": "Quy định về an ninh nghiêm cấm hành vi nào", 
        "activity_id": "81df543a-717e-4092-8378-b753d386f1f1", 
        "expected_chunk_id": "41c5e610-7716-4316-bb2e-8b1a9c41e6ac"
    },
    {
        "query": "Lịch trình tập trung tại Sân B1", 
        "activity_id": "27acacc3-c3e3-4dfa-ab9d-621113c407ae", 
        "expected_chunk_id": "ed3da1d3-1a85-4527-bac7-85370a7875cf"
    },
    {
        "query": "Quà tặng Xuân cho hộ gia đình chính sách", 
        "activity_id": "27acacc3-c3e3-4dfa-ab9d-621113c407ae", 
        "expected_chunk_id": "55fdc6e1-c088-4cb7-a433-856b095f1b13"
    },
    {
        "query": "Quy định về trang phục giày dép", 
        "activity_id": "27acacc3-c3e3-4dfa-ab9d-621113c407ae", 
        "expected_chunk_id": "55fdc6e1-c088-4cb7-a433-856b095f1b13"
    },
    {
        "query": "Tác phong đeo thẻ sinh viên", 
        "activity_id": "27acacc3-c3e3-4dfa-ab9d-621113c407ae", 
        "expected_chunk_id": "34c337d4-e471-412f-bca7-1ec11ed71d8d"
    },
    {
        "query": "Tuyệt đối không tự ý tách đoàn", 
        "activity_id": "27acacc3-c3e3-4dfa-ab9d-621113c407ae", 
        "expected_chunk_id": "50e72ca6-950d-4326-878c-3f92600cb793"
    }
]

@pytest_asyncio.fixture(autouse=True)
async def reset_globals():
    db_mod._pool = None
    chunk_repo_mod._chunk_repo = None
    chunk_service_mod._chunk_service = None
    yield
    if db_mod._pool is not None:
        await db_mod._pool.close()
        db_mod._pool = None

@pytest.mark.asyncio
@pytest.mark.parametrize("scenario", scenarios)
async def test_search_chunks_of_activity(scenario):
    chunk_service = get_chunk_service()
    query = scenario["query"]
    activity_id = uuid.UUID(scenario["activity_id"])
    expected_chunk_id = scenario["expected_chunk_id"]
    
    results = await chunk_service.search_chunks_of_activity(query, top_k=5, activity_id=activity_id)
    
    assert results is not None, f"No results found for query: {query}"
    assert len(results) > 0, f"Empty results for query: {query}"
    
    # results is a list of {"score": ..., "data": {"id": ..., "text_content": ...}}
    top_ids = [str(r["data"]["id"]) for r in results]
    
    assert expected_chunk_id in top_ids[:1], f"Expected Chunk ID {expected_chunk_id} not found in results for query: {query}. Found: {top_ids}"
