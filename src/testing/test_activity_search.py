import pytest
import pytest_asyncio
import uuid
import json
import os
import src.database.database_connect as db_mod
import src.repository.activity_repo as activity_repo_mod
import src.service.activity_service as activity_service_mod
import src.service.chunk_service as chunk_service_mod
from src.service.activity_service import get_activity_service

# Load test data from the JSON file
def load_test_data():
    file_path = os.path.join("src", "testing", "DB_Table", "activity_table.json")
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

test_data = load_test_data()

# Define 10 test scenarios
scenarios = [
    {"query": "Hỗ trợ phát giấy khen", "expected_id": "b0d9f9da-eb06-438f-82c3-2bb7a9399a9e"},
    {"query": "Trao giấy vinh danh cho mấy anh chị", "expected_id": "b0d9f9da-eb06-438f-82c3-2bb7a9399a9e"},
    {"query": "Dọn dẹp sắp xếp tài liệu", "expected_id": "d60ba952-9a22-490e-94d6-6600bd17ab16"},
    {"query": "Dọn tài liệu", "expected_id": "d60ba952-9a22-490e-94d6-6600bd17ab16"},
    {"query": "Vệ sinh văn phòng", "expected_id": "f06c9356-eb52-4d82-a42c-f30547422f23"},
    {"query": "Giải Bóng chuyền Bách Khoa 2026", "expected_id": "81df543a-717e-4092-8378-b753d386f1f1"},
    {"query": "Cổ vũ bóng chuyền", "expected_id": "81df543a-717e-4092-8378-b753d386f1f1"},
    {"query": "Chiến dịch Xuân Tình Nguyện", "expected_id": "27acacc3-c3e3-4dfa-ab9d-621113c407ae"},
    {"query": "CTV PHÁT GIẤY VINH DANH", "expected_id": "2cbaa84e-a037-408b-a377-a35bac4ef1a0"},
    {"query": "Phát giấy khen", "expected_id": "2cbaa84e-a037-408b-a377-a35bac4ef1a0"},
    {"query": "Dọn dẹp PTN cơ sở 2", "expected_id": "3ec31bb7-daa2-4aa2-ba93-4ff295fdf532"},
    {"query": "Dọn phòng thí nghiệm", "expected_id": "3ec31bb7-daa2-4aa2-ba93-4ff295fdf532"},
    {"query": "Quay video giới thiệu phòng thí nghiệm Yaskawa", "expected_id": "46a341a7-66f2-43f7-9f79-d7ed2bb83361"},
    {"query": "Hỗ trợ phòng thí nghiệm", "expected_id": "46a341a7-66f2-43f7-9f79-d7ed2bb83361"},
    {"query": "Hội thảo Generative AI", "expected_id": "18607c07-b486-4dcd-9524-c5bc4a3ec505"},
    {"query": "Sự kiện AI", "expected_id": "18607c07-b486-4dcd-9524-c5bc4a3ec505"},
    {"query": "phát giấy khen ở A4", "expected_id": "b0d9f9da-eb06-438f-82c3-2bb7a9399a9e"}
]

@pytest_asyncio.fixture(autouse=True)
async def reset_globals():
    db_mod._pool = None
    activity_repo_mod._activity_repo = None
    activity_service_mod._activity_service = None
    chunk_service_mod._chunk_service = None
    yield
    if db_mod._pool is not None:
        await db_mod._pool.close()
        db_mod._pool = None

@pytest.mark.asyncio
@pytest.mark.parametrize("scenario", scenarios)
async def test_search_activity_by_name(scenario):
    activity_service = get_activity_service()
    query = scenario["query"]
    expected_id = scenario["expected_id"]
    
    results = await activity_service.search_activity_by_name(query)
    
    assert results is not None, f"No results found for query: {query}"
    assert len(results) > 0, f"Empty results for query: {query}"
    
    # Check if expected_id is in the top results
    # results is a list of {"score": ..., "data": {"id": ..., "name": ...}}
    top_ids = [str(r["data"]["id"]) for r in results]
    
    assert expected_id in top_ids[:1], f"Expected ID {expected_id} not found in results for query: {query}. Found: {top_ids}"
