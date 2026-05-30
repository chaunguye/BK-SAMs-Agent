

### I. Nhóm 1: Khám phá Hoạt động (Activity Discovery)

**Câu 1: Lọc theo thời gian tương lai gần**

* **User Query:** Tuần sau có hoạt động tình nguyện nào mở đăng ký không bạn?
* **Expected Tool Call:** `search_relevant_activities`
* **Args:** `{"time_start": "2026-05-25T00:00:00Z", "time_end": "2026-05-31T23:59:59Z", "status": "OPEN"}`

**Câu 2: Lọc kết hợp Thời gian và Địa điểm**

* **User Query:** Mình muốn tìm hoạt động nào diễn ra ở Cơ sở Dĩ An trong tháng này.
* **Expected Tool Call:** `search_relevant_activities`
* **Args:** `{"time_start": time_stamp contain "2026-05-27", "time_end": time_stamp contain "2026-05-31", "location": "Cơ sở Dĩ An"}`


---

### II. Nhóm 2: Tra cứu và Truy xuất Tài liệu (RAG - Thao tác 2 bước)

**Câu 3: Tra cứu thông tin cơ bản (Dừng ở bước lấy chi tiết)**

* **User Query:** Cho mình hỏi thời gian diễn ra của hoạt động "Hiến máu nhân đạo 2026" là khi nào?
* **Expected Tool Call 1:** `get_activity_ids_by_name` $\rightarrow$ `{"name": "Hiến máu nhân đạo 2026"}`
* **Expected Tool Call 2:** `get_activity_details` $\rightarrow$ `{"activity_id": "UUID_TỪ_TOOL_1"}`

**Câu 4: Tra cứu thông tin chuyên sâu (Phải trích xuất Chunks - Tóm tắt câu hỏi khong ro rang)**

* **User Query:** Mình là sinh viên năm nhất đang tính đăng ký Chiến dịch Xuân Tình Nguyện mà không biết đi cái này thì nhà trường có quy định bắt buộc phải mặc trang phục như thế nào không ạ?
* **Expected Tool Call 1:** `get_activity_ids_by_name` $\rightarrow$ `{"name": "Chiến dịch Xuân Tình Nguyện"}`
* **Expected Tool Call 2:** `get_activity_details` $\rightarrow$ `{"activity_id": "UUID_XuanTinhNguyen"}`
* **Expected Tool Call 3:** `search_activity_chunks` $\rightarrow$ `{"activity_id": "UUID_XuanTinhNguyen", "query": "quy định trang phục chiến dịch"}` *(Query đã được cô đọng)*

**Câu 5: Tra cứu thông tin chung của hệ thống (Sử dụng Manual Guide)**

* **User Query:** Em mới xài app lần đầu, làm sao để tích hợp mã QR minh chứng sau khi đi hoạt động về vậy admin?
* **Expected Tool Call:** `search_chunks`
* **Args:** `{"query": "tích hợp mã QR minh chứng hoạt động"}` *(Query đã được cô đọng)*

---

### III. Nhóm 3: Xử lý Nhập nhằng & Không tìm thấy (Ambiguity & Not Found)

**Câu 6: Xử lý Nhập nhằng (Trùng tên/Điểm số RRF suýt soát)**

* **User Query:** Xem giúp mình thông tin hội thảo tiếng Anh với.
* **Expected Tool Call:** `get_activity_ids_by_name` $\rightarrow$ `{"name": "hội thảo tiếng Anh"}`
* **Expected Result (Logic):** Hệ thống trả về 2 kết quả có score suýt soát (ví dụ: `Hội thảo tiếng Anh chuyên ngành` và `Hội thảo tiếng Anh giao tiếp`). Agent **KHÔNG** gọi thêm tool nào nữa, dừng lại và xuất danh sách kèm theo Metadata (Thời gian, Địa điểm) để hỏi sinh viên chọn cái nào.

**Câu 7: Xử lý Khi không tìm thấy hoạt động (Score RRF quá thấp < 0.015)**

* **User Query:** Mình muốn xem thể lệ giải đua xe F1 BK-Racing.
* **Expected Tool Call:** `get_activity_ids_by_name` $\rightarrow$ `{"name": "giải đua xe F1 BK-Racing"}`
* **Expected Result (Logic):** Tool trả về score < 0.015. Agent phản hồi trực tiếp: *"Xin lỗi, hiện tại hệ thống không tìm thấy thông tin mà bạn yêu cầu, vui lòng thử lại hoặc liên hệ trực tiếp với Khoa tổ chức hoạt động."*

---

### IV. Nhóm 4: Đăng ký Hoạt động (Activity Registration)

**Câu 8: Đăng ký trực tiếp khi biết rõ tên**

* **User Query:** Đăng ký cho mình tham gia hoạt động "Hội thao sinh viên Bách Khoa" với.
* **Expected Tool Call 1:** `get_activity_id_by_name` $\rightarrow$ `{"name": "Hội thao sinh viên Bách Khoa"}`
* **Expected Tool Call 2:** `register_activity` $\rightarrow$ `{"activity_id": "UUID_HoiThao", "student_id": "UUID_Student"}`

**Câu 9: Đăng ký dựa vào Ngữ cảnh hội thoại trước đó (Context Awareness)**

* **User Context (Tin nhắn trước):** Sinh viên hỏi chi tiết về "Hội thảo Generative AI". Agent đã trả lời kèm ID.
* **User Query (Tin nhắn hiện tại):** Ok nghe hay đó, đăng ký cái này cho mình luôn đi!
* **Expected Tool Call:** `register_activity`
* **Args:** `{"activity_id": "UUID_HoiThao_AI_Từ_Context", "student_id": "UUID_Student"}` *(Không cần gọi lại tool search ID)*

**Câu 10: Đăng ký chung chung không rõ tên hoạt động (Phải gợi ý)**

* **User Query:** Chiều nay mình rảnh quá, có hoạt động nào đăng ký đi liền được không bồ?
* **Expected Tool Call:** `search_relevant_activities`
* **Args:** `{"time_start": "2026-05-23T12:00:00Z", "time_end": "2026-05-23T23:59:59Z", "status": "OPEN"}`
* **Expected Result (Logic):** Agent nhận danh sách hoạt động trả về và gợi ý cho sinh viên chọn.

---

### V. Nhóm 5: Hủy Đăng ký Hoạt động (Unregistration)

**Câu 11: Hủy đăng ký khi ghi rõ tên hoạt động**

* **User Query:** Hủy đăng ký hoạt động "Tiếp sức mùa thi" giùm mình nha.
* **Expected Tool Call 1:** `get_activity_id_by_name` $\rightarrow$ `{"name": "Tiếp sức mùa thi"}`
* **Expected Tool Call 2:** `unregister_activity` $\rightarrow$ `{"activity_id": "UUID_TiepSucMuaThi", "student_id": "UUID_Student"}`

**Câu 12: Hủy đăng ký dựa vào Ngữ cảnh hội thoại**

* **User Context (Tin nhắn trước):** Agent vừa hiển thị xác nhận đăng ký thành công hoạt động "Ngày chủ nhật xanh".
* **User Query:** Chết rồi mình bấm nhầm, hủy cái này đi bạn ơi.
* **Expected Tool Call:** `unregister_activity`
* **Args:** `{"activity_id": "UUID_ChuNhatXanh_Từ_Context", "student_id": "UUID_Student"}`

**Câu 13: Hủy đăng ký không nói tên (Phải lấy danh sách đã đăng ký để user chọn)**

* **User Query:** Mình muốn hủy bớt một hoạt động đã đăng ký tuần sau vì cấn lịch học đột xuất.
* **Expected Tool Call:** `get_registered_activity`
* **Args:** `{"student_id": "UUID_Student"}`
* **Expected Result (Logic):** Agent hiển thị danh sách các hoạt động sinh viên đã đăng ký và hỏi sinh viên muốn xóa hoạt động nào.

---

### VI. Nhóm 6: Kịch bản Nâng cao và Biên (Edge Cases / Stress Testing)

**Câu 14: Lọc hoạt động theo trạng thái cụ thể**

* **User Query:** Tìm cho mình các hoạt động đã đóng link đăng ký rồi được không?
* **Expected Tool Call:** `search_relevant_activities`
* **Args:** `{"status": "CLOSED"}`

**Câu 15: Tìm kiếm nâng cao kết hợp sắp xếp theo Ngày công tác xã hội (Đặc thù HCMUT)**

* **User Query:** Có hoạt động nào mở đăng ký trong tháng 5 mà được nhiều ngày CTX không, xếp từ cao xuống thấp giúp mình nhé.
* **Expected Tool Call:** `search_relevant_activities`
* **Args:** `{"time_start": "2026-05-01T00:00:00Z", "time_end": "2026-05-31T23:59:59Z", "status": "OPEN", "sort_by": "number_of_conversion_day", "desc": true}`

**Câu 16: Ngôn ngữ tiếng Anh (Hệ thống phải tự động chuyển sang phản hồi tiếng Anh)**

* **User Query:** Can you find any seminar about AI computing next week?
* **Expected Tool Call:** `search_relevant_activities`
* **Args:** `{"time_start": "2026-05-25T00:00:00Z", "time_end": "2026-05-31T23:59:59Z", "name": "AI computing"}`
* **Expected Result (Logic):** Agent xử lý và trả lời bằng **tiếng Anh** vì user tương tác bằng tiếng Anh trước.

**Câu 17: Chào hỏi bằng tiếng Anh (Nhưng hệ thống vẫn ưu tiên tiếng Việt)**

* **User Query:** Hello admin! Good morning!
* **Expected Tool Call:** None (Greeting)
* **Expected Result (Logic):** Agent phản hồi bằng **tiếng Việt** (ví dụ: *"Chào bạn! Mình có thể giúp gì cho bạn hôm nay?"*) theo đúng điều kiện ưu tiên của System Prompt.

**Câu 18: Câu hỏi béo phức tạp chứa nhiều thông tin nhiễu cần cô đọng khi tra cứu tài liệu**

* **User Query:** Mình đang ở nhà trọ chán quá tính đăng ký cái hoạt động dọn dẹp vệ sinh khuôn viên trường mà không biết ban tổ chức có hỗ trợ cơm trưa hay nước uống gì không ta, tại ví tiền mình đang cạn rồi hihi.
* **Expected Tool Call 1:** `get_activity_ids_by_name` $\rightarrow$ `{"name": "dọn dẹp vệ sinh khuôn viên trường"}`
* **Expected Tool Call 2:** `get_activity_details` $\rightarrow$ `{"activity_id": "UUID_DonDep"}`
* **Expected Tool Call 3:** `search_activity_chunks` $\rightarrow$ `{"activity_id": "UUID_DonDep", "query": "hỗ trợ cơm trưa nước uống chi phí"}` *(Query cô đọng loại bỏ thông tin nhiễu về nhà trọ/ví tiền)*

**Câu 19: Đăng ký hoạt động khi gõ sai chính tả nhẹ (Trigram xử lý ở tầng Repository, Agent trích xuất từ khóa)**

* **User Query:** Đăng kí hộ tớ cái hoạt động "Họi thảo blockchian" với.
* **Expected Tool Call 1:** `get_activity_id_by_name` $\rightarrow$ `{"name": "Họi thảo blockchian"}`
* **Expected Tool Call 2:** `register_activity` $\rightarrow$ `{"activity_id": "UUID_Blockchain_Từ_Repo", "student_id": "UUID_Student"}`

**Câu 20: Hủy đăng ký một hoạt động cụ thể kèm lọc thời gian bắt đầu**

* **User Query:** Mình muốn hủy lịch đi làm CTV hỗ trợ hiến máu ngày mai.
* **Expected Tool Call 1:** `get_activity_id_by_name` $\rightarrow$ `{"name": "CTV hỗ trợ hiến máu"}`
* **Expected Tool Call 2:** `unregister_activity` $\rightarrow$ `{"activity_id": "UUID_HienMau", "student_id": "UUID_Student"}`

---

Bộ câu hỏi này sẽ giúp bạn và Nam test phủ toàn bộ các hàm từ `search_relevant_activities`, `get_activity_ids_by_name`, `search_activity_chunks` đến các kịch bản giữ/xóa bộ nhớ hội thoại. Bạn có thể nạp đống này vào file JSON test suite của mình nhé!