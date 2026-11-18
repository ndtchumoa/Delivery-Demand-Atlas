# Dự đoán nhu cầu giao hàng theo cụm AOI và tối ưu tuyến chặng cuối (LaDe-D Jilin)

Môn MI3380. Dữ liệu: LaDe-D, thành phố Jilin (`data/raw/delivery_jl.csv`, 31.415 đơn, 12/5–28/10).
Dự báo số đơn nhận mỗi ngày theo `region_id × aoi_type`; bước tối ưu tuyến CVRP (OR-Tools) dùng AOI làm nút.

## Trạng thái

| Hạng mục | Trạng thái |
|---|---|
| Làm sạch, kiểm tra chất lượng, EDA | Hoàn thành (`notebooks/01_eda.ipynb`) |
| Bảng nhu cầu (41 chuỗi × 170 ngày; 1.259 AOI × 170 ngày) | Hoàn thành |
| Đặc trưng một-ngày-trước, chia theo thời gian, kiểm tra rò rỉ | Hoàn thành (`02_features.ipynb`) |
| Baseline dự báo và đánh giá | Hoàn thành (`03_forecasting.ipynb`) |
| Mô hình học máy (LightGBM/XGBoost) | Đã đánh giá trên validation (`04_ml_validation.ipynb`) |
| Demo dự báo trước một ngày | Hoàn thành. So sánh ba mô hình trên validation và xem baseline đã chọn trên test. |
| Cụm AOI, CVRP và kịch bản S0–S3 | Chưa triển khai (`04_routing.ipynb` chưa có) |

## Cấu trúc

```
data/raw/                 dữ liệu gốc (không sửa)
data/processed/           bảng đã xử lý, bảng đặc trưng, cấu hình cửa sổ ổn định
src/config.py             đường dẫn và tham số chung
src/data_loader.py        đọc dữ liệu thô, tập phân tích, bảng nhu cầu
src/preprocessing.py      làm sạch, cờ chất lượng, cửa sổ ổn định, bảng nhu cầu và AOI
src/features.py           lag, trung bình trượt, đặc trưng lịch
src/train_forecast.py     baseline dự báo
src/evaluate_forecast.py  MAE, RMSE, WAPE; chọn mô hình trên tập kiểm định
src/build_forecast_demo.py tạo demo từ dự báo và chỉ số đã lưu
src/visualization.py      hàm vẽ dùng chung
notebooks/                01_eda, 02_features, 03_forecasting
outputs/forecasts/        dự báo, chỉ số, giao thức đánh giá
outputs/figures/          hình do notebook tạo
tests/                    kiểm thử đơn vị
```

## Chạy lại

```bash
pip install -r requirements.txt
python -m src.preprocessing
python -m src.train_forecast
python -m src.evaluate_forecast
python -m unittest discover -s tests -v
```

Các notebook chạy theo thứ tự `01_eda` → `02_features` → `03_forecasting`; mỗi notebook tự gọi các bước cần thiết và kết thúc bằng phần Kết luận.

## Quy ước và giả định

- `ds` là ngày nhận đơn; đại lượng dự báo là số đơn nhận mỗi ngày.
- Tệp gốc không bị sửa. Tọa độ gần (0,0) được đặt về NaN; 8 đơn có thời gian giao trên 24 giờ bị loại khỏi tập phân tích và ghi trong `data/processed/excluded_rows.csv`; đơn thiếu `accept_gps` hoặc có thời gian giao bằng 0 được giữ và đánh cờ.
- Tệp không ghi năm; năm 2022 là quy ước kỹ thuật, nên đặc trưng thứ trong tuần không phải kết luận thực nghiệm.
- Ngày toàn thành phố không có đơn nào là ngày không quan sát, không phải nhu cầu bằng 0.
- Cửa sổ chính 27/6–2/10: huấn luyện 27/6–23/8, kiểm định 24/8–12/9, kiểm tra 13/9–2/10. Toàn kỳ 12/5–28/10 được chạy như kịch bản độ nhạy.

## Kết quả hiện có

Trên tập kiểm tra của cửa sổ chính (820 ô = 41 chuỗi × 20 ngày, 4.732 đơn), baseline `rolling_mean_7` (được chọn trên tập kiểm định) đạt MAE 1,3115, RMSE 3,2093, WAPE 22,73% ở cấp chuỗi; WAPE 14,94% sau khi cộng theo `region_id`.

### Demo dự báo Jilin

Tải [Demo_Du_bao_Jilin.html](outputs/forecasts/demo/Demo_Du_bao_Jilin.html) và mở bằng trình duyệt. Demo chạy offline và hỗ trợ xem số đơn thực tế, dự báo theo ngày, vùng và loại AOI. Cửa sổ chính có 820 dòng validation (5.300 đơn) và 820 dòng test (4.732 đơn). Validation so sánh trung bình trượt 7 ngày, LightGBM và XGBoost. Test hiển thị trung bình trượt 7 ngày, baseline được chọn trên validation.

- [Dự báo chi tiết](outputs/forecasts/demo/Du_bao_Jilin.csv)
- [Chỉ số đánh giá](outputs/forecasts/demo/Chi_so_Du_bao_Jilin.csv)

Để tạo lại demo từ các kết quả đã lưu trong repo, chạy từ thư mục gốc:

```bash
python -m src.build_forecast_demo
```

## Giới hạn

- Cửa sổ ổn định, việc loại 8 đơn trên 24 giờ và danh mục AOI đều dựa trên toàn bộ dữ liệu quan sát, nên đánh giá mang tính hồi cứu.
- Nguyên nhân của đợt giảm đơn từ 3/10 không được ghi trong tài liệu bộ dữ liệu; phân tích chỉ cho thấy phần lớn mức giảm đi cùng số shipper hoạt động giảm.
- Trong kịch bản toàn kỳ chỉ 14 trong 34 ngày kiểm tra có thể chấm điểm.

## Đồng bộ thiết kế và kiểm tra trước commit

Tâm GPS tiếp nhận của từng region là thống kê mô tả về phân bố không gian của điểm tiếp nhận; không dùng làm vị trí kho. Theo v4, hệ thống dùng một depot chung, xác định riêng bằng dữ liệu train ở bước chuẩn bị định tuyến. Hiện chưa có cấu hình CVRP hoặc vị trí depot đã fit.

Danh sách cột học máy dùng chung tại `configs/forecast_features.json`, đọc qua `src.feature_schema.featureColumns()`. Cả LightGBM và XGBoost phải sử dụng danh sách này; ablation bỏ cột theo nhóm. Giữ `day_of_week` và `is_weekend` làm ứng viên RQ2. Centroid và mật độ AOI được tính từ lịch sử train phù hợp với từng dòng, như mô tả trong [thiết kế đặc trưng không gian](docs/04_spatial_ml_design.md). Không dùng `demand`, `observed_demand` hoặc các cột đánh giá làm đầu vào.

### Độ nhạy giữ đủ đơn

Chạy `python -m src.sensitivity_keep_all_orders` hoặc notebook `02_sensitivity_keep_all_orders.ipynb`. Giao thức và tiêu chí được khai báo trước lần chạy đầu trong `configs/sensitivity_keep_all_orders.json`. Đánh giá validation, cùng cửa sổ và cùng ô, A loại đơn >24 giờ, B giữ đủ đơn với cùng làm sạch GPS. Kết quả nằm riêng tại `outputs/forecasts/sensitivity_keep_all_orders/`, không ghi đè baseline chính.

Kết quả baseline: thứ hạng sáu mô hình không đổi ở cả hai cửa sổ; thay đổi MAE tương đối lớn nhất khoảng 0,136%, nhỏ hơn ngưỡng 1%. Quy tắc loại 8 đơn không thay đổi kết luận lựa chọn baseline trên validation trong giao thức này. Chưa suy rộng sang LightGBM/XGBoost hoặc định tuyến; phải chạy lại A/B sau khi có mô hình học máy.

### Thứ tự công việc tiếp theo

1. Lặp đánh giá độ nhạy giữ đủ đơn với LightGBM và XGBoost.
2. Xác định ánh xạ AOI, depot chung và F/Q bằng train, rồi kiểm tra AOI mới và AOI đa region.
3. Chạy CVRP S0–S3 trên validation. Sau khi chốt, lưu cấu hình thực tế vào `configs/routing_locked.json` rồi commit trước khi chạy test.

Cấu hình định tuyến khóa phải chứa: quy tắc và phiên bản ánh xạ AOI/cụm, depot và dữ liệu train nguồn, F/Q, quy tắc chia xe/dự trữ, tách nút, phạt bỏ nút, chiến lược/timing/seed solver nếu có, đơn vị và cách làm tròn khoảng cách, lambda, epsilon Gap closed và tập ngày đánh giá. Hiện chưa tạo file `routing_locked.json` vì solver và các tham số thực tế chưa được triển khai.


## Đặc trưng không gian và ML: validation

Thiết kế và kế hoạch: [docs/04_spatial_ml_design.md](docs/04_spatial_ml_design.md).
Kết quả: [docs/04_ml_validation_results.md](docs/04_ml_validation_results.md) và [notebook](notebooks/04_ml_validation.ipynb).

```bash
python -m pip install -r requirements.txt
python -m src.preprocessing
python -m src.train_ml --scenario all
python -m unittest discover -s tests -v
```

Lệnh ML mặc định chạy cửa sổ chính; `--scenario all` thêm độ nhạy toàn kỳ.
Đợt này chỉ chấm validation, chưa chấm test ML. Kết quả lưu trong
`outputs/forecasts/ml_validation/`; hai mô hình full có định dạng native kèm schema mã hoá.
Thống kê không gian của dòng train chỉ dùng các ngày trước đó; validation dùng lookup cuối train.
ML hiện chưa vượt baseline rolling 7 ngày trên validation; chưa có kết luận hiệu quả định tuyến.
