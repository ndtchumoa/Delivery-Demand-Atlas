# Kế hoạch và thiết kế đặc trưng không gian – dự báo ML

Ngày: 17/11/2026. Cơ sở: `main` tại `65dab315`; đề cương MI3380 trong `reports/De_cuong_chi_tiet_MI3380.docx`.

Người dùng đã chọn **chỉ chạy validation trong đợt này**. Chưa chấm test ML. Đợt này hoàn thiện đặc trưng không gian, hai mô hình học máy, so sánh baseline, importance và ablation. Kết quả trên validation là kết quả phát triển, chưa phải kết luận cuối về RQ1–RQ2.

## 1. Kế hoạch, đầu ra và tiêu chí hoàn thành

| Bước | Công việc | Đầu ra | Tiêu chí |
|---|---|---|---|
| 1 | Đối chiếu đề cương và bản sửa EDA/UTF-8 | Thiết kế này | Dùng bản sửa đã merge; giữ quy ước ngày, chuỗi và splits |
| 2 | Bổ sung centroid, mật độ và fallback | `src/spatial_features.py`, lookup theo scenario | Chỉ fit train; thay tương lai không làm đổi đặc trưng quá khứ; giữ region gốc |
| 3 | Huấn luyện pooled LightGBM/XGBoost | `src/train_ml.py`, `configs/ml_experiment.json` | Hai họ mô hình cùng đầu vào, seed, tập ô; chọn bằng validation |
| 4 | So sánh baseline, importance, ablation, nhóm nhu cầu | CSV và notebook `04_ml_validation.ipynb` | MAE/RMSE/WAPE ở chuỗi và region; đủ bốn nhóm ablation |
| 5 | Kiểm thử, tái chạy, lưu bằng chứng | Tests, manifest, native models, metadata | Không có test ML metrics; nạp lại mô hình khớp dự báo |
| 6, đợt sau | Rà soát giao thức và độ nhạy giữ đủ đơn cho ML | Báo cáo A/B và quyết định chốt | Không điều chỉnh dựa trên test |
| 7, đợt sau | Depot, vùng phân bổ, F/Q và CVRP | Thiết kế định tuyến và chạy validation S0–S3 | Chốt bằng train/validation trước khi chạy test |

## 2. Hợp đồng dữ liệu

- Đầu vào: `demand_panel.csv`, tập đơn `delivery_jl_analysis.parquet` sinh từ tiền xử lý và `stable_period.json`.
- Một dòng dự báo: `series_id = region_id × aoi_type`, ngày `ds_date`, nhãn `demand` là số đơn tiếp nhận theo ds.
- Không đổi 41 chuỗi, cửa sổ hoặc quy tắc loại tám đơn. Danh mục địa lý toàn kỳ vẫn mang tính hồi cứu như đề cương đã nêu.
- Ngày toàn thành phố không có bản ghi vẫn là chưa quan sát; không dùng làm nhãn hoặc thay bằng 0 trong lịch sử. Ngày có quan sát nhưng một chuỗi không có đơn giữ 0.
- Train chính: 27/6–23/8; validation: 24/8–12/9; test: 13/9–2/10. Năm 2022 là quy ước kỹ thuật.
- Giữ 14 ngày warmup; chỉ dùng dòng có `history_ready` và `city_observed`. Lịch sử lag/rolling chỉ dùng đến t−1. Mô hình cố định sau train, cập nhật đầu vào lịch sử mỗi ngày theo rolling one-day-ahead.

## 3. Đặc trưng không gian

### 3.1. Định nghĩa cụ thể

Với các đơn lịch sử được phép dùng, nhóm theo **region gốc × loại AOI × AOI**; tính median cặp toạ độ đích `lng`, `lat` của từng AOI trong nhóm. Loại cặp thiếu, ngoài miền hợp lệ hoặc gần (0,0) khỏi phần toạ độ, vẫn giữ đơn trong số đếm.

Centroid chuỗi là trung bình toạ độ của các tâm AOI hợp lệ, mỗi AOI một trọng số. Đây là tâm mô tả của các AOI quan sát trong chuỗi, không phải depot và không phải tâm GPS tiếp nhận. AOI nhiều region được giữ riêng trong mỗi region gốc; không dùng region phổ biến nhất để chuyển đơn.

`historical_density = tổng đơn lịch sử / (số AOI lịch sử × số ngày toàn thành phố có quan sát trong lịch sử)`.

Đơn vị là **đơn/AOI/ngày quan sát**, không phải đơn/km². Mẫu số ngày là lịch quan sát của thành phố để không chỉ lấy những ngày chuỗi có đơn. Số AOI đếm cả AOI thiếu GPS; centroid chỉ dùng AOI có GPS hợp lệ. Hai phần đo lường khác nhau và không được diễn giải thành mật độ địa lý thực.

### 3.2. Thời điểm fit và fallback

| Dòng cần tạo đặc trưng | Dữ liệu được dùng |
|---|---|
| Train tại ngày t | Đơn và ngày quan sát thuộc train, trước t |
| Validation | Toàn bộ train đến hết ngày cuối train, giữ cố định |
| Test trong giai đoạn sau | Lookup cuối train đã lưu; không fit lại bằng test |

Cách tính mở rộng trong train ngăn mật độ của một dòng chứa chính nhãn hoặc nhãn ở các ngày train sau nó. Chỉ fit một thống kê trên toàn train rồi áp cho mọi dòng train có thể khiến thống kê mật độ chứa nhãn của chính dòng đó.

Fallback: chuỗi → region → toàn bộ lịch sử train; thay đồng thời centroid và mật độ khi không đủ thống kê. `spatial_fallback` lần lượt là 0, 1, 2. Khi toàn bộ train không có GPS hợp lệ, dừng với lỗi rõ ràng. Không tự lấy GPS validation/test để lấp thiếu.

AOI mới tại validation không cập nhật centroid hoặc mật độ. Dự báo vẫn ở mức chuỗi, không cần một dòng dự báo riêng cho AOI mới. **Ánh xạ AOI mới xuống nút/cụm định tuyến là đầu việc khác, chưa được hoàn thành bằng fallback dự báo này.**

### 3.3. Chi phí tính toán

Hiện tính lại lookup cho từng ngày train đủ điều kiện; phù hợp tập Jilin khoảng 31 nghìn đơn. Chi phí xấp xỉ O(T × N log N), không dành cho dữ liệu hàng triệu đơn. Khi mở rộng có thể dùng cập nhật tăng dần và lưu trạng thái, nhưng phải giữ nguyên kiểm thử as-of.

## 4. Thiết kế mô hình và lựa chọn cấu hình

- Một mô hình pooled cho tất cả chuỗi trong mỗi scenario, không huấn luyện riêng 41 mô hình với lịch sử ngắn.
- Nhóm đầu vào: calendar, lag, rolling, spatial, lấy từ schema chung. Không có `demand`, split hay cờ chấm điểm trong đầu vào.
- `region_id`, `aoi_type`, `day_of_week` dùng one-hot với danh mục học từ các dòng train đủ điều kiện; giá trị mới mã hoá toàn 0. Lưu danh mục và thứ tự cột để suy luận giống huấn luyện.
- Hai họ mô hình dùng cùng bình phương sai số, learning rate 0,05; regularization L2 = 1. Dự báo chặn dưới 0, giữ số thực, chưa làm tròn trước khi cộng region.
- LightGBM CPU, `deterministic=True`, `force_col_wise=True`; XGBoost CPU `tree_method=hist`; một luồng, seed 2026. Không khẳng định kết quả bit-for-bit giữa hệ điều hành/phiên bản thư viện khác nhau.
- Không early stopping trong đợt này: số cây là một phần lưới nhỏ được ghi trước, tránh thêm một cơ chế chọn không được ghi nhận.

| Họ mô hình | Lưới | Số ứng viên/biến thể |
|---|---|---:|
| LightGBM | num_leaves {7,15}; min_child_samples {20,50}; n_estimators {100,300} | 8 |
| XGBoost | max_depth {2,4}; min_child_weight {5,20}; n_estimators {100,300} | 8 |

Mỗi họ có bản full và bốn bản bỏ từng nhóm, tổng 80 lượt fit/scenario; chạy hai scenario là 160 lượt. Lưới đã cố định trước khi xem kết quả ML đầu tiên. Không mở rộng lưới sau khi nhìn test.

Chọn trong từng biến thể bằng WAPE validation cấp chuỗi thấp nhất; hoà thì MAE thấp hơn, sau đó mã ứng viên. Chọn giữa hai bản ML full theo cùng quy tắc. Ablation là phân tích khám phá, không tự biến thành mô hình chính mới. Không refit bằng validation, không chấm test trong CLI của đợt này.

## 5. Đánh giá và diễn giải

- Dùng lại hàm MAE/RMSE/WAPE hiện có. WAPE là tổng sai số tuyệt đối / tổng nhu cầu; WAPE 0,2 nghĩa tổng độ lớn sai số bằng 20% tổng đơn, không phải mọi chuỗi đều sai 20%.
- Tất cả mô hình và baseline phải khớp chính xác khoá chuỗi–ngày. Đánh giá thêm sau khi cộng các loại AOI theo region.
- Baseline tốt nhất chọn bằng validation trong sáu baseline. Giữ `historical_weekday` cho S1 sau này, dù baseline dự báo tốt nhất là phương pháp khác.
- Ablation bỏ cả nhóm và chọn lại tám cấu hình trong cùng họ. Delta = WAPE bản bỏ nhóm − WAPE full. Delta dương: bỏ nhóm làm tệ hơn; âm: bỏ nhóm giúp cải thiện trong đợt validation này. Không suy ra quan hệ nhân quả hoặc thứ hạng đóng góp ổn định.
- Native gain: gộp các cột one-hot về biến gốc, chuẩn hoá trong từng mô hình. Đây là phân bổ độ giảm loss trên train, có thiên lệch do tương quan; không so trực tiếp số gain thô giữa hai thư viện.
- Nhóm nhu cầu thấp/vừa/cao dựa trên trung bình nhãn của các ngày train đủ điều kiện; ngưỡng phân vị 1/3 và 2/3 fit từ train. Không dùng tổng nhu cầu test để phân nhóm hoặc loại chuỗi.

## 6. Đầu ra và tái lập

Mỗi scenario trong `outputs/forecasts/ml_validation/` có:

| Tệp | Nội dung |
|---|---|
| `protocol.json` | Chọn mô hình, splits, schema, seed, giao thức và ngưỡng nhóm nhu cầu |
| `spatial_train_{series,region,global}.csv` | Lookup cuối train, số đơn/AOI/ngày quan sát và centroid |
| `features_train_validation.parquet` | Đặc trưng đủ điều kiện; không có dòng test |
| `validation_search.csv` | Toàn bộ ứng viên và metrics chọn cấu hình |
| `validation_predictions.csv` | Dự báo validation ML full, ablations và sáu baseline |
| `validation_metrics.csv` | Metrics cấp chuỗi và region |
| `validation_ablation.csv` | Sai khác WAPE khi bỏ từng nhóm |
| `validation_demand_bands.csv` | Sai số theo nhóm nhu cầu cho ML full được chọn và baseline được chọn |
| `gain_importance.csv` | Native gain theo biến của các biến thể |
| `*_metadata.json` | Cấu hình được chọn, cột mã hoá và danh mục train |
| `*_full.txt`, `*_full.json` | Hai mô hình full, định dạng native; ablation giữ metadata và kết quả để giảm dung lượng |

`run_manifest.json` ghi phiên bản môi trường và SHA-256 đầu vào, code và cấu hình. `requirements-ml-tested.txt` ghi các phiên bản lõi đã chạy, không phải khoá toàn bộ phụ thuộc notebook. Chưa xác minh chạy ML trên Windows/Python 3.13; cần tái chạy ở máy người dùng trước khi tuyên bố tương thích môi trường đó.

```bash
python -m pip install -r requirements.txt
# Tuỳ chọn dùng đúng phiên bản lõi đã kiểm chứng:
python -m pip install -r requirements-ml-tested.txt
python -m src.preprocessing
python -m src.train_ml --scenario all
python -m unittest discover -s tests -v
```

## 7. Việc cần chốt trước giai đoạn tiếp theo

1. Rà soát hiệu năng validation trước khi khoá giao thức test. ML full hiện chưa vượt rolling baseline; giữ kết quả này, không giả định boosting phải tốt hơn.
2. Chạy độ nhạy giữ đủ tám đơn cho ML với cùng giao thức. Cửa sổ toàn kỳ và giữ đủ tám đơn là **hai thí nghiệm khác nhau**; đợt này chỉ có cửa sổ toàn kỳ, chưa có A/B ML giữ đủ đơn.
3. Nếu muốn thử loss MAE/Poisson, residual quanh rolling baseline hoặc lưới khác: tạo phiên bản giao thức mới, công bố mở rộng từ validation, không dùng test để lựa chọn.
4. Trước CVRP: kiểm tra địa lý region/13 AOI đa region; chọn đơn vị phân bổ; xác định depot chung từ train; hiệu chỉnh F/Q đạt mức sử dụng hợp lý; định nghĩa ánh xạ AOI mới. Chưa cần chốt F/Q trong đợt dự báo này.
5. Chốt vai trò của mô hình dùng cho S2 nếu baseline vẫn vượt ML. Báo cáo riêng so sánh ML và baseline, giữ S1 lịch sử cùng thứ theo đề cương; không âm thầm thay định nghĩa S1 hoặc S2.

## Tài liệu kỹ thuật

- [LightGBM parameters](https://lightgbm.readthedocs.io/en/stable/Parameters.html): deterministic CPU và force_col_wise.
- [LightGBM LGBMRegressor](https://lightgbm.readthedocs.io/en/stable/pythonapi/lightgbm.LGBMRegressor.html).
- [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html).
- [XGBoost native model IO](https://xgboost.readthedocs.io/en/stable/tutorials/saving_model.html).
