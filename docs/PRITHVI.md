# Prithvi 작물 분류 추론 (이슈 #28)

2026-11-15 16:20 KST · 레인: Prithvi · 브랜치 `feat/prithvi`

## 무엇을 돌렸나

| 항목 | 값 |
| --- | --- |
| 모델 | `ibm-nasa-geospatial/Prithvi-EO-1.0-100M-multi-temporal-crop-classification` (Apache-2.0, DOI 10.57967/hf/0954). 체크포인트 `multi_temporal_crop_classification_Prithvi_100M.pth`(1.68 GB). HF 저장소의 `config.yaml`은 0바이트이므로 설정은 같은 저장소의 `multi_temporal_crop_classification_Prithvi_100M.py`(mmseg config)를 썼다 |
| 방식 | **추론만** 했다. 미세조정, 추가 학습, RL은 없다. CPU(torch 2.14.1+cpu, 8 스레드), 오프라인 배치이며 요청 경로 밖이다 |
| 코드 | mmseg·mmcv·terratorch 없이, 공개 config가 가리키는 모듈(TemporalViTEncoder 6블록·768차원·8헤드 → ConvTransformerTokensToEmbeddingNeck → FCNHead)을 순수 PyTorch로 옮겼다: [`model_api/vision/prithvi_crop.py`](../model_api/vision/prithvi_crop.py). 체크포인트 키는 보조 헤드(학습 전용)만 빼고 `strict` 수준으로 전부 일치한다. 추가 의존성은 없다(기존 `/srv/hackathon/venv`의 torch만 사용) |
| 입력 | HLS v2.0 L30/S30 6밴드(Blue, Green, Red, Narrow NIR, SWIR1, SWIR2) × 3시점, 224×224 칩(30 m, 해당 HLS 타일의 UTM 격자), 필지 중심점 기준. 정규화는 config의 means/stds. 공개 test pipeline과 똑같이 `(18,H,W)`에 평범한 `reshape(6,3,H,W)`를 적용했다(모델이 이 순서로 학습됨) |
| 시점 선택 | W1 4/15–5/31, W2 6/1–7/31, W3 8/1–9/30. 창마다 칩의 Fmask 무효 비율(구름·인접·그림자·눈 비트 1–4, 또는 fill)이 가장 낮은 그라뉼을 골랐다(장면 구름량 순으로 탐색). 남은 무효 픽셀은 밴드 평균으로 채웠다(정규화 후 0) |
| 수집 | [`model_api/vision/fetch_hls_chips.py`](../model_api/vision/fetch_hls_chips.py): `earthaccess`(netrc)로 COG 창을 HTTPS에서 순차로 읽었다. 파일을 읽을 때마다 0.6 s 이상 쉬어 호스트당 2 req/s 이하로 유지했다. 칩은 `/srv/hackathon/data/raw/hls_prithvi/chips/`에 있고 커밋하지 않는다 |
| 적재 | [`model_api/vision/run_prithvi.py`](../model_api/vision/run_prithvi.py) → `vision_result`에 upsert(PK `field_id, year, model_id`). 다른 테이블은 건드리지 않았다 |
| 대상 | 데모 필지 20개(`field_ndvi_hls`·`field_et_openet`에 있는 CSB 필지): Story County(19169) 12개, IL 17113 3개, NE 31109 3개, OH 39159 2개. 연도 2024 |

### 지표 정의

- `crop_pred`: CSB 폴리곤 안 픽셀의 Prithvi 최빈 클래스(공식 13클래스 이름).
- `class_fractions`: 폴리곤 안 13클래스별 비율(jsonb).
- `bare_fraction`: 폴리곤 안 픽셀 중 `Developed/Barren` 또는 `Fallow/Idle Cropland`로 분류된 비율. 공식 목록에서 맨땅·휴경에 해당하는 클래스는 이 두 개뿐이다. 시즌 내 맨땅 기간을 직접 잰 값이 아니다.
- `agreement_with_cdl`: 폴리곤 안 픽셀 중 Prithvi 클래스가 CDL 2024 픽셀과 같은 비율(0–1). CDL 2024는 `/srv/hackathon/data/raw/cdl/tier2_*`의 카운티 30 m 클립을 칩 격자에 최근린 재투영한 것이다. CDL 코드는 **이름이 1:1로 대응하는 것만** 비교했다: 1 Corn, 5 Soybeans, 24 Winter Wheat, 36 Alfalfa, 61 Fallow/Idle Cropland, 2 Cotton, 4 Sorghum, 111 Open Water, 141–143 Forest. 그 밖의 코드는 분모에서 뺐다(아래 주의 3).

## 시간

| 단계 | 시간 |
| --- | --- |
| 체크포인트 다운로드(HF) | 1분 미만 |
| HLS 칩 수집, 20필지 × 3시점 | 약 20분(필지당 38–91 s, 순차 처리와 레이트 제한 포함) |
| 모델 로드 | 1.7 s |
| 추론 | 칩당 평균 3.0 s(CPU 8스레드), 20필지 합계 62.6 s(재투영·적재 포함) |

## 필지별 결과 (2024)

| field_id | 카운티 | HLS 날짜 | crop_pred | CDL 2024 (field_crop_history) | agreement_with_cdl | bare_fraction | 상위 클래스 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 171825001292309 | 17113 | 05-22 S30; 06-14 L30; 09-02 L30 | Soybeans | Soybeans | 0.945 | 0.010 | Soy 0.91, Corn 0.04 |
| 171825006921423 | 17113 | 05-19 S30; 06-14; 09-02 | Corn | Corn | 0.997 | 0.006 | Corn 0.99 |
| 171825006923844 | 17113 | 05-19 S30; 06-14; 09-02 | Corn | Corn | 0.882 | 0.002 | Corn 0.87, Soy 0.13 |
| 191825000014952 | 19169 | 04-24; 06-26; 09-07 | **Corn** | **Soybeans** | **0.193** | 0.016 | Corn 0.78, Soy 0.19 |
| 191825001175247 | 19169 | 04-24; 06-26; 09-07 | Soybeans | Soybeans | 0.924 | 0.029 | Soy 0.95 |
| 191825001176098 | 19169 | 04-24; 06-26; 09-07 | Soybeans | Soybeans | 0.989 | 0.021 | Soy 0.96 |
| 191825001176345 | 19169 | 04-24; 06-26; 09-07 | Soybeans | Soybeans | 0.971 | 0.013 | Soy 0.98 |
| 191825001176875 | 19169 | 05-18; 06-26; 09-07 | Soybeans | Soybeans | 0.966 | 0.046 | Soy 0.94 |
| 191825001177094 | 19169 | 04-24; 06-26; 09-07 | Soybeans | Soybeans | 0.985 | 0.020 | Soy 0.98 |
| 191825002945908 | 19169 | 04-24; 06-26; 09-07 | Soybeans | Soybeans | 0.956 | 0.030 | Soy 0.97, Fallow 0.03 |
| 191825003867870 | 19169 | 04-24; 06-26; 09-07 | Corn | Corn | 0.980 | 0.018 | Corn 0.98 |
| 191825003868071 | 19169 | 04-24; 06-26; 09-07 | Corn | Corn | 0.879 | 0.028 | Corn 0.92, Soy 0.05 |
| 191825003868102 | 19169 | 04-24; 06-26; 09-07 | Corn | Corn | 0.932 | 0.012 | Corn 0.91, Soy 0.08 |
| 191825003868954 | 19169 | 04-24; 06-26; 09-07 | Corn | Corn | 0.936 | 0.043 | Corn 0.90, Soy 0.05 |
| 191825003869023 | 19169 | 04-24; 06-26; 09-07 | Corn | Corn | 0.825 | 0.066 | Corn 0.79, Soy 0.13 |
| 311825001242480 | 31109 | 04-16; 06-09; 08-04 | Corn | Corn | 0.899 | 0.042 | Corn 0.87, Soy 0.07 |
| 311825002820374 | 31109 | 04-21; 06-09; 08-04 | Soybeans | Soybeans | 0.866 | 0.039 | Soy 0.78, Corn 0.18 |
| 311825008109480 | 31109 | 04-21; 06-05; 08-04 | Soybeans | Soybeans | 0.997 | 0.000 | Soy 1.00 |
| 391825000729943 | 39159 | 04-22; 07-27; 09-14 | Corn | Corn | 0.676 | 0.027 | Corn 0.62, Soy 0.33 |
| 391825009407249 | 39159 | 04-22; 07-27; 09-14 | Corn | Corn | 0.865 | 0.005 | Corn 0.83, Soy 0.15 |

센서를 따로 적지 않은 날짜는 모두 HLSL30이다. 칩 날짜, 센서, 폴리곤 픽셀 수, 무효 비율은 `vision_result.notes`와 `/srv/hackathon/data/raw/hls_prithvi/pred/report_2024.json`에 있다.

**요약**: 필지 최빈 클래스가 CDL 2024 필지 작물과 같은 필지는 **20개 중 19개**다. 픽셀 일치율(`agreement_with_cdl`)의 평균은 **0.883**이다. 유일하게 어긋난 191825000014952(28.7 ha, CDL 2024 Soybeans 0.93)는 옥수수–콩 교대 필지다(2023 Corn, 2025 Corn). 모델은 옥수수로 봤다. 원인은 확인하지 못했다(미확인). 작은 필지라 칩 가장자리 혼합이나 시점 선택의 영향일 수 있다.

## API 확인

`model_api`를 로컬(`uvicorn model_api.main:app --port 8791`, 읽기 전용 DB)로 띄워 `GET /field/191825003867870/profile`을 호출했다. `vision`은 `{"model_id": "...crop-classification", "crop_pred": "Corn", "bare_fraction": 0.02, "agreement_with_cdl": 0.98}`로 채워졌고, `info_gaps`의 "Prithvi vision result not loaded yet" 문구는 사라졌다. API 코드와 스키마는 바꾸지 않았다.

## 주의 (화면·설명에 함께 쓸 것)

1. **모델 카드 성능은 aAcc 60.64 %, mIoU 0.4269**다(mAcc 64.06 %. Corn IoU 0.5491, Soybeans IoU 0.5297). 이 데모의 20필지 일치율 0.883은 옥수수·콩 단작 필지가 대부분이라 나온 값이다. 일반 성능으로 인용하지 않는다.
2. 학습 데이터는 2022년 HLS **S30** 장면(3–9월 중 이른·중간·늦은 시점 3개)과 잡음이 있는 CDL 라벨이다. 이번 입력은 2024년이고 대부분 **L30**이다. 시점 창도 우리가 정했다(W1–W3). 분포가 달라질 수 있다.
3. 공식 CDL→13클래스 재분류표는 **미확인**이다. 데이터셋 카드는 클래스 이름만 준다. 학습 데이터 저장소의 `cdl_freq.csv`는 번호 체계가 카드와 다르다(예: Alfalfa 36과 Fallow 61이 기타로 들어감). 그래서 `agreement_with_cdl`은 이름이 1:1로 대응하는 CDL 코드에서만 계산했고, 공식 평가 지표가 아니다.
4. `bare_fraction`은 시즌 내 맨땅 기간이 아니라 "맨땅·휴경 클래스로 분류된 픽셀 비율"이다. 맨땅 기간은 HLS NDVI(`/field/{id}/bare-periods`)를 쓴다.
5. 칩은 필지 중심 224×224(6.7 km)다. 폴리곤 경계 픽셀은 30 m 혼합 화소라 주변 피복이 섞일 수 있다.
6. Prithvi는 **보조 레이어**다. 작물 라벨의 기준은 CDL이다(SOT 1.5: 실패 시 CDL). 화면에서 판단을 대신하는 값으로 쓰지 않는다.

## 재현

```bash
source /srv/hackathon/venv/bin/activate            # torch CPU, earthaccess, rasterio, geopandas, psycopg
# 체크포인트: huggingface_hub.hf_hub_download(<model repo>, <file>, local_dir=/srv/hackathon/data/raw/hls_prithvi/model)
python -m model_api.vision.fetch_hls_chips 2024    # ~/.netrc Earthdata, 칩 -> /srv/hackathon/data/raw/hls_prithvi/chips
python -m model_api.vision.run_prithvi 2024        # 추론 + vision_result upsert (PG* env)
```

단위 테스트 `model_api/tests/test_prithvi_crop.py`(랜덤 가중치, 체크포인트 불필요)는 torch가 없는 환경에서 skip된다.
