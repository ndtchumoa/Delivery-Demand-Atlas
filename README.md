# Trực quan hóa nhu cầu giao hàng chặng cuối tại Jilin trên OpenStreetMap và phân tích đa chuỗi thời gian theo vùng

Đồ án MI3380 sử dụng LaDe-D để khảo sát vị trí điểm giao và diễn biến số đơn của bốn vùng ở Jilin. Đơn được tính theo ngày người giao tiếp nhận. Phần phân tích theo vùng đã chạy được. Bản đồ OpenStreetMap sẽ dùng dữ liệu tổng hợp theo ô H3.

- [Đề cương chi tiết](reports/project_proposal.md) gồm câu hỏi nghiên cứu, phương pháp và tiêu chí nghiệm thu.
- [Kế hoạch triển khai](docs/implementation_plan.md) ghi thứ tự công việc và đầu ra từng bước.
- [Notebook phân tích đa chuỗi](notebooks/02_regional_time_series.ipynb) trình bày dữ liệu, biểu đồ và tương quan giữa các vùng.

## Dữ liệu

[Tệp LaDe-D Jilin](data/raw/delivery_jl.csv) có 31.415 đơn, 4 mã vùng và 163 ngày có bản ghi trong 170 ngày lịch. Các đơn giao quá 24 giờ vẫn được tính vào số đơn tiếp nhận. Số 0 biểu thị vùng không có đơn ghi nhận vào một ngày thành phố có dữ liệu. Bảy ngày không có bản ghi ở cả thành phố được để trống. Năm 2022 trên tệp xuất là quy ước để biểu diễn ngày nguồn ở dạng ISO.

## Chạy phân tích

Từ thư mục gốc, dùng Python 3.12 trở lên với môi trường riêng nếu cần.

```bash
python -m pip install "pandas>=3,<4" "numpy>=2,<3"
python -m src.regional_time_series
python -m unittest discover -s tests -p test_regional_time_series.py -v
```

Ba tệp được xuất vào `outputs/analysis/`:

| Tệp | Nội dung |
| --- | --- |
| [regional_daily_demand.csv](outputs/analysis/regional_daily_demand.csv) | Một dòng mỗi vùng–ngày, kèm cờ ngày quan sát. |
| [regional_summary.csv](outputs/analysis/regional_summary.csv) | Tổng đơn, số ngày quan sát, trung bình, trung vị, độ lệch chuẩn và số ngày không có đơn ghi nhận. |
| [regional_correlations.csv](outputs/analysis/regional_correlations.csv) | Pearson và số ngày ghép cặp cho hai cách đo ở toàn kỳ và cửa sổ đối chiếu. |

Để chạy notebook, cài thêm `matplotlib` và `jupyter`, rồi mở `notebooks/02_regional_time_series.ipynb`. Các chương trình dự báo và kiểm thử cũ dùng bộ [requirements.txt](requirements.txt).

Ở toàn kỳ, vùng 53 và 129 có tương quan theo mức số đơn khoảng 0,81 và theo sai phân ngày khoảng 0,51. Vùng 31 và 165 giảm từ khoảng 0,53 xuống 0,01 khi chuyển sang sai phân. Cửa sổ 27/06–02/10 cho kết quả khác ở một số cặp. Các hệ số mô tả cách chuỗi biến động trong từng giai đoạn.

## Mốc dự báo

Notebook, mô hình, đầu ra đánh giá và demo dự báo có trong [nhánh forecast-v1](https://github.com/ndtchumoa/jilin-delivery-demand-atlas/tree/forecast-v1). Có thể tải trực tiếp [HTML dự báo](https://github.com/ndtchumoa/jilin-delivery-demand-atlas/blob/forecast-v1/outputs/forecasts/demo/forecast_jilin.html) để mở offline.

Tài liệu dữ liệu, H3, Leaflet và điều kiện sử dụng nền bản đồ được dẫn trong [đề cương](reports/project_proposal.md#6-tài-liệu-nền).
