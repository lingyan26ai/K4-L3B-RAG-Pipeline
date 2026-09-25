# RAG evaluation results

## Run information

| Field                              | Value |
| ---------------------------------- | ----- |
| Evaluation date                    | 25/09/2026 (23:21, giờ Việt Nam) |
| Framework and version              | Ragas 0.4.3 |
| Evaluator model                    | OpenRouter `openai/gpt-4o-mini` |
| Generator model                    | OpenRouter `openai/gpt-4o-mini` |
| Embedding model                    | Retrieval: `BAAI/bge-m3`; chấm answer relevance: `openai/text-embedding-3-small` |
| Corpus version/commit              | Corpus tại `ee0708c` (không đổi trong lượt đo); code đánh giá tại `dc37986`. Gồm 3 tài liệu chính sách, 5 trang tuyển sinh, 224 chunks. |
| Golden dataset size                | 15 câu hỏi có đáp án và context tham chiếu |
| `top_k`                            | 5 |
| Fallback threshold and calibration | Cosine `0,55`, hiệu chỉnh trên 7 câu đúng chủ đề (thấp nhất `0,6203`) và 7 câu ngoài chủ đề (cao nhất `0,4799`). Fallback không tham gia A/B; PageIndex chưa được kiểm chứng qua API thật vì chưa có key. |

## Configurations

- **Config A — dense-only:** Tìm kiếm vector bằng `BAAI/bge-m3` trên ChromaDB, lấy 5 đoạn có cosine score cao nhất.
- **Config B — hybrid + RRF:** Lấy tối đa 10 đoạn từ dense và 10 đoạn từ BM25L, hợp nhất bằng RRF một lần, trả 5 đoạn đầu.

Hai config dùng cùng 15 câu golden, generator, evaluator, prompt và `top_k`; chỉ thay retrieval strategy.

## Overall scores

| Metric            | Config A | Config B | Delta B−A |
| ----------------- | -------: | -------: | --------: |
| Faithfulness      |   0,8333 |   0,7722 |   −0,0611 |
| Answer relevance  |   0,8626 |   0,8390 |   −0,0236 |
| Context recall    |   0,9000 |   0,9000 |    0,0000 |
| Context precision |   0,8748 |   0,7111 |   −0,1637 |
| **Average**       | **0,8677** | **0,8056** | **−0,0621** |

## A/B comparison

- Cấu hình tốt hơn: **A (dense-only)** trên lượt đo này.
- Evidence: A cao hơn B ở faithfulness, answer relevance và context precision; context recall bằng nhau. Cả 15 câu đều có đủ bốn điểm cho hai cấu hình trong `reports/openrouter_full.json`. Chênh lệch lớn nhất là context precision (`−0,1637` cho B), cho thấy danh sách hybrid chứa thêm đoạn kém liên quan theo bộ chấm hiện tại.
- Trade-off về latency/cost: B cần thêm BM25L và RRF; chưa lưu thời gian xử lý và chi phí API theo từng cấu hình, nên chưa định lượng được chênh lệch. Số điểm trên là chất lượng câu trả lời, không phải số đo tốc độ hay chi phí.

## Worst performers

|  # | Question | Config | Faithfulness | Relevance | Recall | Precision | Failure stage             | Root cause |
| -: | -------- | ------ | -----------: | --------: | -----: | --------: | ------------------------- | ---------- |
|  1 | Bốn phẩm chất ứng viên VinUni nên thể hiện (câu 6) | B | 0,0000 | 0,9080 | 0,0000 | 0,0000 | retrieval/generation | Top 5 có file `article_03` nhưng thiếu `news/article_03.md::chunk-2` chứa đáp án; model nêu sai cả bộ bốn phẩm chất. |
|  2 | Bốn phẩm chất ứng viên VinUni nên thể hiện (câu 6) | A | 0,3333 | 0,9052 | 0,0000 | 0,4167 | retrieval/generation | Cũng thiếu `chunk-2`; câu trả lời thay **Commitment** bằng **Academic**. |
|  3 | Có phải nộp đơn riêng cho học bổng merit-based (câu 3) | B | 1,0000 | 0,9645 | 0,5000 | 0,2000 | retrieval | Câu trả lời đúng nhưng Ragas chỉ đánh giá một phần nhỏ trong 5 đoạn lấy về là hữu ích; context chứa nhiều đoạn không phục vụ câu hỏi. |

## Recommendations

| Priority | Action | Evidence from failure analysis | Expected impact | How to verify |
| -------: | ------ | ------------------------------ | --------------- | ------------- |
| 1 | Thử bổ sung đoạn liền kề khi retrieval lấy trúng file nguồn nhưng thiếu đoạn trả lời. | Câu 6: cả A/B bỏ sót `news/article_03.md::chunk-2`; recall đều bằng 0 và đáp án sai. | Có thêm bằng chứng về đúng bốn phẩm chất trong context; chưa khẳng định điểm sẽ tăng trước khi đo lại. | Kiểm tra `chunk-2` trong top 5/context, câu trả lời nêu đủ **Outstanding Ability, Aspiration, Creativity, Commitment**, rồi chạy lại 15 câu. |
| 2 | Giảm đoạn nhiễu ở hybrid bằng điều chỉnh RRF hoặc bước rerank theo mức liên quan, giữ cùng `top_k=5`. | Câu 3 của B có context precision `0,2000`; trung bình context precision B thấp hơn A `0,1637`. | Dự kiến tăng context precision mà không làm giảm context recall. | So sánh lại 4 metric trên cùng 15 câu với baseline A/B, đồng thời xem top 5 của câu 3. |
| 3 | Bảo đảm câu hỏi theo mã quy định dẫn đúng đoạn pháp lý trước khi tạo citation. | Câu 14: cả A/B thiếu `legal/GDL-SAM-004-V2.1_Scholarship-Financial-Aid_2025.md::chunk-8`; câu trả lời OpenRouter dựa trên bài viết thay vì điều khoản gốc. | Câu trả lời có bằng chứng trực tiếp từ văn bản được hỏi. | Kiểm tra `chunk-8` xuất hiện trong context và `[Document n]` trỏ đúng văn bản GDL-SAM-004-V2.1; đo lại 15 câu để kiểm tra tác động chung. |

## Bonus experiments

| Experiment | Baseline | Metric delta | Latency/cost delta | Conclusion |
| ---------- | -------- | -----------: | -----------------: | ---------- |
| Chưa thực hiện bonus experiment | A/B ở trên | Chưa đo | Chưa đo | Không đưa ra kết luận về bonus. |
