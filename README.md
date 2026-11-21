# Atlas nhu cầu giao hàng chặng cuối tại Jilin

Đồ án MI3380 phân tích số đơn tiếp nhận theo ngày của bốn vùng trong LaDe-D Jilin. Phân tích đa chuỗi đã chạy được. Bản đồ tương tác trên nền OpenStreetMap sẽ hiển thị số đơn theo ô H3.

## Tái tạo phân tích

Từ thư mục gốc, dùng Python 3.12 trở lên.

```bash
python -m pip install -r requirements.txt
python -m src.regional_time_series
python -m unittest discover -s tests -v
```

Dữ liệu nguồn nằm tại [delivery_jl.csv](data/raw/delivery_jl.csv). Lệnh phân tích xuất ba bảng vào [outputs/analysis](outputs/analysis).

| Tệp | Nội dung |
| --- | --- |
| `regional_daily_demand.csv` | Số đơn và cờ quan sát theo vùng–ngày. |
| `regional_summary.csv` | Thống kê mô tả theo vùng. |
| `regional_correlations.csv` | Tương quan Pearson và số ngày ghép cặp. |

Để xem biểu đồ, cài thêm `matplotlib` và `jupyter` rồi chạy [notebook phân tích đa chuỗi](notebooks/02_regional_time_series.ipynb).

## Tài liệu

- [Đề cương](reports/project_proposal.md) trình bày dữ liệu, phương pháp và tiêu chí nghiệm thu.
- [Kế hoạch triển khai](docs/implementation_plan.md) ghi các bước còn lại cho bản đồ và báo cáo.
- [Nhánh lưu trữ dự báo](https://github.com/ndtchumoa/jilin-delivery-demand-atlas/tree/archive/demand-forecasting) lưu notebook EDA, mã, mô hình và kết quả của giai đoạn trước. [Demo dự báo HTML](https://github.com/ndtchumoa/jilin-delivery-demand-atlas/blob/archive/demand-forecasting/outputs/forecasts/demo/forecast_jilin.html).
