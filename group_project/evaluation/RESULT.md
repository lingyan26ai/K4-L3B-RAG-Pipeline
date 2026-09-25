# Báo cáo nhóm — RAG tuyển sinh VinUni

**Ngày:** 25/09/2026 · **Commit:** `ee0708c`

## Dữ liệu và pipeline

- Corpus gồm 3 tài liệu chính sách và 5 trang tuyển sinh VinUni; 15 câu hỏi và đáp án tham chiếu trong `group_project/evaluation/golden_dataset.json`.
- Tài liệu được chuẩn hóa thành Markdown, chia thành 224 chunks, embed bằng `BAAI/bge-m3` và lưu trong ChromaDB. Retrieval gồm dense, BM25L và hợp nhất RRF; chatbot dùng Streamlit.
- Ngưỡng fallback `0,55` được chọn từ 7 câu đúng chủ đề (cosine thấp nhất `0,6203`) và 7 câu ngoài chủ đề (cao nhất `0,4799`), theo `calibration_result.json`. Chưa kiểm chứng PageIndex qua API thật.

## A/B comparison — So sánh retrieval

Trên **cùng 15 câu golden**, `top_k=5`: A dùng dense; B dùng dense + BM25L + RRF. Hai cấu hình dùng cùng prompt và Gemini `gemini-3.5-flash-lite` để tạo câu trả lời và chấm bằng Ragas `0.4.3`; fallback không tham gia A/B. Kết quả chi tiết ở `reports/ab_ragas_results.json`.

| Chỉ số | A: dense | B: hybrid |
|---|---:|---:|
| Nguồn đúng trong top 5 | 15/15 | 15/15 |
| MRR@5 theo file nguồn | 1,000 | 0,933 |

Chỉ số trên đo **file nguồn**, chưa khẳng định chunk chứa đúng bằng chứng. Hybrid đưa file nguồn của 2 câu về hạng 2 thay vì hạng 1.

## Overall scores — Đánh giá câu trả lời

| Chỉ số Ragas (trung bình 15 câu) | A: dense | B: hybrid | B − A |
|---|---:|---:|---:|
| Faithfulness | 0,889 | 0,778 | −0,111 |
| Answer relevance | 0,791 | 0,809 | +0,018 |
| Context recall | 0,933 | 0,933 | 0,000 |
| Context precision | 0,813 | 0,650 | −0,163 |
| **Trung bình 4 chỉ số** | **0,857** | **0,793** | **−0,064** |

Dense cao hơn ở faithfulness và context precision, bằng ở context recall; hybrid nhỉnh hơn nhẹ ở answer relevance. Hai câu khó nhất là **bốn phẩm chất tuyển sinh** và **quy định nâng cấp học bổng**: cả A/B đều bỏ sót chunk chứa bằng chứng trực tiếp từ nguồn được hỏi, nên model trả lời sai hoặc từ chối. Điểm do LLM chấm cần đọc cùng câu trả lời gốc; chưa đo chi phí/độ trễ API.

## Worst performers — Hai câu trả lời yếu nhất

Hai câu khó nhất là **bốn phẩm chất tuyển sinh** và **quy định nâng cấp học bổng**: cả A/B đều tìm đúng file nguồn nhưng bỏ sót chunk chứa bằng chứng trực tiếp. Cần đọc `source_id` và câu trả lời của từng câu trong `ab_ragas_results.json` khi đánh giá lỗi này.

## Recommendations — Hướng cải thiện

Ưu tiên cải thiện lấy đúng chunk cho hai câu lỗi rồi chạy lại cùng bộ 15 câu. Kiểm tra PageIndex bằng API thật khi có key; với cấu hình hiện tại chỉ kiểm tra được nhánh dự phòng.

Demo ngày 25/09/2026: câu hỏi về hồ sơ bị loại ở vòng sơ tuyển được Gemini trả lời với `[Document 5]`, khớp nguồn hiển thị `news/article_01.md::chunk-2`; câu hỏi về thay pin iPhone nhận câu từ chối an toàn và không hiện nguồn. Toàn bộ **20/20 test** đạt. Các sửa lỗi cache model, thứ tự nguồn citation và từ chối khi điểm dense dưới ngưỡng được thực hiện **sau** benchmark A/B ở trên; các số Ragas là baseline của commit `ee0708c`, chưa đo lại trên phiên bản đã sửa.
