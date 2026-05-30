import pytest
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.tools import DeferredToolRequests
import uuid
import json

# =================================================================
# INSTRUCTIONS FOR WRITING END-TO-END TESTS:
# 1. Provide the 'user_query'.
# 2. Run using 'await real_agent.run(user_query, deps=live_deps)'.
#    (Note: This uses your LIVE database and LIVE LLM API)
# 3. Use 'get_tool_calls(result)' to inspect LLM behavior.
# 4. Assert tool names or actual text output.
# =================================================================

import pytest_asyncio

def get_tool_calls(result):
    """Helper to extract all tool calls made by the LLM in a run."""
    calls = []
    for msg in result.all_messages():
        if isinstance(msg, ModelResponse):
            for part in msg.parts:
                if isinstance(part, ToolCallPart):
                    # Ensure args is a dict
                    if isinstance(part.args, str):
                        try:
                            part.args = json.loads(part.args)
                        except:
                            pass
                    calls.append(part)
    return calls

@pytest_asyncio.fixture(autouse=True)
async def reset_singletons():
    """Reset singletons to avoid 'Event loop is closed' issues in tests."""
    import src.database.database_connect as db_conn
    import src.repository.activity_repo as act_repo
    import src.service.activity_service as act_serv
    import src.service.chunk_service as chunk_serv
    
    # Close pool if it exists and loop is open
    if db_conn._pool is not None:
        try:
            # Only try to close if the loop is still running
            import asyncio
            if not db_conn._pool._loop.is_closed():
                await db_conn._pool.close()
        except:
            pass
        db_conn._pool = None
    
    # Reset singletons
    act_repo._activity_repo = None
    act_serv._activity_service = None
    chunk_serv._chunk_service = None

@pytest.mark.asyncio
async def test_ut_01_discovery_dian(real_agent, live_deps):
    """
    UT-01: 'Tuần tới ở cơ sở Dĩ An có hoạt động tình nguyện nào mở đăng ký không bạn?'
    Expect: call search_relevant_activities with location='Cơ sở Dĩ An' and status='OPEN'.
    """
    user_query = "Tuần tới ở cơ sở Dĩ An có hoạt động tình nguyện nào mở đăng ký không bạn?"
    result = await real_agent.run(user_query, deps=live_deps)
    
    tool_calls = get_tool_calls(result)
    print(f"\n[UT-01 QUERY]: {user_query}")
    print(f"[TOOL CALLS]: {[c.tool_name for c in tool_calls]}")
    
    assert any(c.tool_name == "search_relevant_activities" for c in tool_calls)
    relevant_call = [c for c in tool_calls if c.tool_name == "search_relevant_activities"][0]
    
    # Assert LLM extracted 'Dĩ An' and 'OPEN' status
    args = relevant_call.args
    location = args.get("location") if isinstance(args, dict) else ""
    status = args.get("status") if isinstance(args, dict) else ""
    
    assert "Dĩ An" in str(location)
    assert status == "OPEN"

@pytest.mark.asyncio
async def test_ut_03_unique_match_details(real_agent, live_deps):
    """
    UT-03: 'Cho mình xin lịch trình chi tiết vụ phát giấy vinh danh tốt nghiệp đợt này với'
    Expect: identify activity and call get_activity_details.
    Truth: ID '2cbaa84e-a037-408b-a377-a35bac4ef1a0' is the Graduation Support activity.
    """
    user_query = "Cho mình xin lịch trình chi tiết vụ phát giấy vinh danh tốt nghiệp đợt này với"
    result = await real_agent.run(user_query, deps=live_deps)
    
    tool_calls = get_tool_calls(result)
    tool_names = [c.tool_name for c in tool_calls]
    print(f"\n[UT-03 QUERY]: {user_query}")
    print(f"[TOOL NAMES]: {tool_names}")
    
    assert "get_activity_ids_by_name" in tool_names
    assert "get_activity_details" in tool_names
    
    details_call = [c for c in tool_calls if c.tool_name == "get_activity_details"][0]
    # Check if it targeted the correct UUID (based on our DB Truth)
    assert str(details_call.args.get("activity_id")) == "2cbaa84e-a037-408b-a377-a35bac4ef1a0"

@pytest.mark.asyncio
async def test_ut_04_rag_workshop_ai(real_agent, live_deps):
    """
    UT-04: 'Mình muốn xem thông tin hội thảo AI'
    Expect: find the Generative AI workshop and potentially search chunks or get details.
    Truth: activity_id '18607c07-b486-4dcd-9524-c5bc4a3ec505'.
    """
    user_query = "Mình muốn xem thông tin hội thảo AI"
    result = await real_agent.run(user_query, deps=live_deps)
    
    tool_calls = get_tool_calls(result)
    tool_names = [c.tool_name for c in tool_calls]
    print(f"\n[UT-04 QUERY]: {user_query}")
    print(f"[TOOL NAMES]: {tool_names}")
    
    assert "get_activity_ids_by_name" in tool_names
    # It might call get_activity_details or search_activity_chunks
    assert any(name in tool_names for name in ["get_activity_details", "search_activity_chunks"])

@pytest.mark.asyncio
async def test_scenario_01_discovery_to_reg(real_agent, live_deps):
    """
    Scenario 01: Multi-turn flow (Discovery -> Details -> Registration)
    """
    # TURN 1: Discovery
    res1 = await real_agent.run("Tuần tới có hoạt động nào không?", deps=live_deps)
    print(f"\n[Scenario 01] Turn 1 Response: {res1.output}")
    
    # TURN 2: Details about "Bóng chuyền" (assuming it was found)
    history = res1.all_messages()
    res2 = await real_agent.run("Sự kiện bóng chuyền đó yêu cầu trang phục thế nào?", deps=live_deps, message_history=history)
    print(f"[Scenario 01] Turn 2 Response: {res2.output}")
    
    # Expect RAG to find "áo thun cổ động của trường (màu xanh truyền thống)"
    assert any(word in str(res2.output).lower() for word in ["áo thun", "đồng phục", "uniform", "màu xanh"])
    
    # TURN 3: Registration
    history = res2.all_messages()
    res3 = await real_agent.run("Ok, đăng ký tham gia giúp mình luôn đi!", deps=live_deps, message_history=history)
    print(f"[Scenario 01] Turn 3 Response type: {type(res3.output)}")
    
    assert isinstance(res3.output, DeferredToolRequests)
    assert any(req.tool_name == 'register_activity' for req in res3.output.approvals)

@pytest.mark.asyncio
async def test_scenario_04_unreg_selection(real_agent, live_deps):
    """
    Scenario 04: Multi-turn Unregistration
    """
    # TURN 1: Generic request
    res1 = await real_agent.run("Hủy đăng ký hoạt động giúp mình với!", deps=live_deps)
    print(f"\n[Scenario 04] Turn 1 Response: {res1.output}")
    
    # TURN 2: User selects one (Assuming list was shown)
    history = res1.all_messages()
    # Let's say the student was registered for 'Xuân Tình Nguyện' in Turn 1 output
    res2 = await real_agent.run("Cái chiến dịch Xuân Tình Nguyện nha bot", deps=live_deps, message_history=history)
    print(f"[Scenario 04] Turn 2 Response: {res2.output}")
    
    assert isinstance(res2.output, DeferredToolRequests)
    assert any(req.tool_name == 'unregister_activity' for req in res2.output.approvals)

@pytest.mark.asyncio
async def test_guest_block_registration(real_agent, live_guest_deps):
    """
    Verify guest users are blocked from registration.
    """
    user_query = "Đăng ký tham gia hoạt động bóng chuyền"
    result = await real_agent.run(user_query, deps=live_guest_deps)
    
    print(f"\n[Guest Test] Response: {result.output}")
    output_text = str(result.output).lower()
    assert any(word in output_text for word in ["guest", "khách", "không được", "chưa đăng nhập", "không thể đăng ký"])

@pytest.mark.asyncio
async def test_scenario_01_discovery_future(real_agent, live_deps):
    """
    Câu 1: Lọc theo thời gian tương lai gần
    'Tuần sau có hoạt động tình nguyện nào mở đăng ký không bạn?'
    """
    user_query = "Tuần sau có hoạt động tình nguyện nào mở đăng ký không bạn?"
    result = await real_agent.run(user_query, deps=live_deps)
    
    tool_calls = get_tool_calls(result)
    print(f"\n[Scenario 01] Tool Calls: {[c.tool_name for c in tool_calls]}")
    
    assert any(c.tool_name == "search_relevant_activities" for c in tool_calls)
    relevant_call = [c for c in tool_calls if c.tool_name == "search_relevant_activities"][0]
    assert relevant_call.args.get("status") == "OPEN"

@pytest.mark.asyncio
async def test_scenario_04_rag_clothing_rules(real_agent, live_deps):
    """
    Câu 4: Tra cứu thông tin chuyên sâu (Phải trích xuất Chunks)
    'Mình là sinh viên năm nhất đang tính đăng ký Chiến dịch Xuân Tình Nguyện mà không biết đi cái này thì nhà trường có quy định bắt buộc phải mặc trang phục như thế nào không ạ?'
    """
    user_query = "Mình là sinh viên năm nhất đang tính đăng ký Chiến dịch Xuân Tình Nguyện mà không biết đi cái này thì nhà trường có quy định bắt buộc phải mặc trang phục như thế nào không ạ?"
    result = await real_agent.run(user_query, deps=live_deps)
    
    tool_calls = get_tool_calls(result)
    tool_names = [c.tool_name for c in tool_calls]
    print(f"\n[Scenario 04] Tool Names: {tool_names}")
    
    assert "get_activity_ids_by_name" in tool_names
    assert "search_activity_chunks" in tool_names
    
    # Check if search_activity_chunks was called with relevant query
    rag_call = [c for c in tool_calls if c.tool_name == "search_activity_chunks"][0]
    assert any(word in str(rag_call.args.get("query")).lower() for word in ["trang phục", "quần", "áo", "đồng phục"])

@pytest.mark.asyncio
async def test_scenario_07_not_found(real_agent, live_deps):
    """
    Câu 7: Xử lý Khi không tìm thấy hoạt động
    'Mình muốn xem thể lệ giải đua xe F1 BK-Racing.'
    """
    user_query = "Mình muốn xem thể lệ giải đua xe F1 BK-Racing."
    result = await real_agent.run(user_query, deps=live_deps)
    
    print(f"\n[Scenario 07] Response: {result.output}")
    output_text = str(result.output).lower()
    # Should indicate it couldn't find it
    assert any(word in output_text for word in ["không tìm thấy", "xin lỗi", "không có", "no activity found"])

@pytest.mark.asyncio
async def test_scenario_08_direct_registration(real_agent, live_deps):
    """
    Câu 8: Đăng ký trực tiếp khi biết rõ tên
    'Đăng ký cho mình tham gia hoạt động "Chiến dịch Xuân Tình Nguyện 2026 (Cấp Khoa)" với.'
    """
    user_query = 'Đăng ký cho mình tham gia hoạt động "Chiến dịch Xuân Tình Nguyện 2026 (Cấp Khoa)" với.'
    result = await real_agent.run(user_query, deps=live_deps)
    
    print(f"\n[Scenario 08] Response Type: {type(result.output)}")
    
    assert isinstance(result.output, DeferredToolRequests)
    assert any(req.tool_name == 'register_activity' for req in result.output.approvals)
    
    # Verify the ID matches our known DB ID for Xuân Tình Nguyện
    reg_req = [req for req in result.output.approvals if req.tool_name == 'register_activity'][0]
    # The tool takes ActivityDetails object, but let's check what's in the args
    args = reg_req.args
    assert "27acacc3-c3e3-4dfa-ab9d-621113c407ae" in str(args)

@pytest.mark.asyncio
async def test_scenario_11_direct_unregistration(real_agent, live_deps):
    """
    Câu 11: Hủy đăng ký khi ghi rõ tên hoạt động
    'Hủy đăng ký hoạt động "Hội thảo Generative AI & Tương lai của Kỹ sư Phần mềm" giùm mình nha.'
    """
    user_query = 'Hủy đăng ký hoạt động "Hội thảo Generative AI & Tương lai của Kỹ sư Phần mềm" giùm mình nha.'
    result = await real_agent.run(user_query, deps=live_deps)
    
    print(f"\n[Scenario 11] Response Type: {type(result.output)}")
    
    assert isinstance(result.output, DeferredToolRequests)
    assert any(req.tool_name == 'unregister_activity' for req in result.output.approvals)
    
    unreg_req = [req for req in result.output.approvals if req.tool_name == 'unregister_activity'][0]
    # ID for Generative AI workshop: 18607c07-b486-4dcd-9524-c5bc4a3ec505
    assert "18607c07-b486-4dcd-9524-c5bc4a3ec505" in str(unreg_req.args)

@pytest.mark.asyncio
async def test_scenario_16_english_language(real_agent, live_deps):
    """
    Câu 16: Ngôn ngữ tiếng Anh (Hệ thống phải tự động chuyển sang phản hồi tiếng Anh)
    'Can you find any seminar about AI computing next week?'
    """
    user_query = "Can you find any seminar about AI computing next week?"
    result = await real_agent.run(user_query, deps=live_deps)
    
    print(f"\n[Scenario 16] Response: {result.output}")
    # The output should be primarily in English
    # Checking for common English words that would likely appear in a response about AI seminars
    english_words = ["seminar", "workshop", "conference", "found", "activity", "details", "next week", "ai"]
    output_lower = str(result.output).lower()
    assert any(word in output_lower for word in english_words)
