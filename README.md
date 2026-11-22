# Atlas nhu cầu giao hàng chặng cuối tại Jilin

Đồ án MI3380 phân tích số đơn tiếp nhận theo ngày của bốn vùng trong LaDe-D Jilin. Repo có quy trình tái tạo phân tích đa chuỗi và so sánh độ phân giải H3. Bản đồ tương tác trên nền OpenStreetMap sẽ hiển thị số đơn theo ô H3.

## Tái tạo phân tích

Từ thư mục gốc, dùng Python 3.12 trở lên.

```bash
python -m pip install -r requirements.txt
python -m src.regional_time_series
python -m src.spatial_aggregation
python -m unittest discover -s tests -v
```

Dữ liệu nguồn nằm tại [delivery_jl.csv](data/raw/delivery_jl.csv). Các lệnh phân tích xuất bảng vào [outputs/analysis](outputs/analysis).

| Tệp | Nội dung |
| --- | --- |
| `regional_daily_demand.csv` | Số đơn và cờ quan sát theo vùng–ngày. |
| `regional_summary.csv` | Thống kê mô tả theo vùng. |
| `regional_correlations.csv` | Tương quan Pearson và số ngày ghép cặp. |
| `spatial_coverage.csv` | Số đơn đủ điều kiện hiển thị theo vùng và toàn thành phố. |
| `h3_resolution_comparison.csv` | Số ô có dữ liệu, tỷ lệ ô ít đơn và tỷ lệ đơn nằm trong các ô ít đơn ở mức 8 và 9. |

Để xem biểu đồ, cài thêm `matplotlib` và `jupyter` rồi chạy hai notebook dưới đây.

- [01 — Phân tích đa chuỗi theo vùng](notebooks/01_regional_time_series.ipynb)
- [02 — Độ phủ tọa độ và so sánh H3](notebooks/02_spatial_coverage.ipynb)

## Tài liệu

- [Đề cương](reports/project_proposal.md) trình bày dữ liệu, phương pháp và tiêu chí nghiệm thu.
- [Kế hoạch triển khai](docs/implementation_plan.md) ghi các bước còn lại cho bản đồ và báo cáo.
- [Nhánh lưu trữ dự báo](https://github.com/ndtchumoa/jilin-delivery-demand-atlas/tree/archive/demand-forecasting) lưu notebook EDA, mã, mô hình và kết quả của giai đoạn trước. [Demo dự báo HTML](https://github.com/ndtchumoa/jilin-delivery-demand-atlas/blob/archive/demand-forecasting/outputs/forecasts/demo/forecast_jilin.html).
