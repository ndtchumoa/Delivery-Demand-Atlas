# Atlas nhu cầu giao hàng chặng cuối tại Jilin

Đồ án MI3380 phân tích số đơn tiếp nhận theo ngày của bốn vùng trong LaDe-D Jilin. Repo có quy trình tái tạo phân tích đa chuỗi và so sánh độ phân giải H3. Bản demo hiển thị số đơn theo ô H3 trên nền OpenStreetMap.

## Mở bản đồ

Từ thư mục gốc, chạy `python -m http.server 8000 --directory demo` rồi mở [http://localhost:8000](http://localhost:8000). Trình duyệt cần kết nối Internet để tải Leaflet 1.9.4 và nền OpenStreetMap.

Bộ lọc ngày, vùng và loại AOI cập nhật tổng đơn và lớp ô. Chọn một ô để xem số đơn từng ngày theo cùng bộ lọc. Chú giải dùng các khoảng số đơn cố định để đối chiếu màu giữa các lần lọc. Bộ đếm ngày cho biết số ngày có dữ liệu trong khoảng chọn. Nền bản đồ ghi công OpenStreetMap trực tiếp trên bản đồ.

## Tái tạo phân tích

Từ thư mục gốc, dùng Python 3.12 trở lên.

```bash
python -m pip install -r requirements.txt
python -m src.regional_time_series
python -m src.spatial_aggregation
python -m src.map_data
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

## Dữ liệu bản đồ

Lệnh `python -m src.map_data` xuất H3 mức 8 vào [demo/data](demo/data).

| Tệp | Nội dung |
| --- | --- |
| [h3_cells.geojson](demo/data/h3_cells.geojson) | Một đa giác cho mỗi ô có đơn. Trường `id` là mã H3 dùng để nối với dữ liệu đếm. |
| [daily_cell_demand.json](demo/data/daily_cell_demand.json) | Lịch quan sát và số đơn tổng hợp theo ngày tiếp nhận, ô H3, vùng và loại AOI. |

Trong phần `orders_by_date`, mỗi dòng có thứ tự `[h3_cell, region_id, aoi_type, orders]` và chỉ xuất khi số đơn dương. Với ngày có cờ `calendar` là `true`, tổ hợp bộ lọc không có dòng tương ứng có 0 đơn được vẽ. Ngày có cờ `false` thiếu quan sát cấp thành phố. Năm 2022 là quy ước kỹ thuật của dữ liệu.

## Tài liệu

- [Đề cương](docs/project_proposal.md) trình bày dữ liệu, phương pháp và tiêu chí nghiệm thu.
- [Kế hoạch triển khai](docs/implementation_plan.md) ghi các bước còn lại cho bản đồ và báo cáo.
