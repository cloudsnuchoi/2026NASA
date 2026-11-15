# Prithvi vs USDA CDL — one definition, one sentence

2026-11-15 KST · lane SITE2 · source: `vision_result` table (PostgreSQL `fieldshift`, 20 rows, year 2024, model `ibm-nasa-geospatial/Prithvi-EO-1.0-100M-multi-temporal-crop-classification`) joined with `field_crop_history` (year 2024). Method and caveats: [PRITHVI.md](PRITHVI.md).

## The sentence everyone must use

> **For 2024, Prithvi's most common class matched the USDA Cropland Data Layer crop on 19 of 20 pilot fields; per-field pixel agreement with CDL ranged from 0.193 to 0.997 (median 0.934, mean 0.883). Most pilot fields are uniform corn or soybean fields, so this is not a general accuracy figure (model card: 60.64 % aAcc).**

Korean (site tabs):

> **2024년 기준 Prithvi 필지 최빈 클래스가 USDA CDL 작물과 같은 필지는 20개 중 19개이고, 필지별 CDL 픽셀 일치율은 0.193–0.997(중앙값 0.934, 평균 0.883)이다. 대부분 옥수수·콩 단작 필지라 일반 정확도가 아니다(모델 카드 aAcc 60.64 %).**

Short form (cards, slides): "Prithvi = CDL on 19 of 20 pilot fields (2024); pixel agreement median 0.934, mean 0.883 — not a general accuracy figure."

## Definitions (two measures, both from the same run)

| Measure | Definition | Where stored |
| --- | --- | --- |
| **Pixel agreement** (`agreement_with_cdl`) | Share (0–1) of the pixels inside the CSB field polygon where the Prithvi class equals the CDL 2024 pixel (CDL nearest-neighbour reprojected to the chip grid). Only CDL codes with a 1:1 name match are compared (1 Corn, 5 Soybeans, 24 Winter Wheat, 36 Alfalfa, 61 Fallow/Idle, 2 Cotton, 4 Sorghum, 111 Open Water, 141–143 Forest); other codes are left out of the denominator. | `vision_result.agreement_with_cdl`, served as `vision.agreement_with_cdl` in `GET /field/{id}/profile` |
| **Field-majority match** | `vision_result.crop_pred` (most common Prithvi class in the polygon) equals `field_crop_history.crop_name` for 2024 (CDL majority crop in the polygon). | derived (join), not stored |

The **one definition used for the distribution numbers is pixel agreement**. The majority-match count is reported next to it as a count, never as a percentage accuracy. Neither is an official evaluation metric (the official CDL→13-class mapping is unconfirmed, see PRITHVI.md caveat 3).

## Numbers (20 demo fields, 2024)

| Statistic | Value |
| --- | --- |
| Fields | 20 (Story IA 12, McLean IL 3, Lancaster NE 3, Union OH 2) |
| Pixel agreement — min | **0.193** (field 191825000014952) |
| Pixel agreement — median | **0.934** (mean of 10th/11th values 0.932 and 0.936) |
| Pixel agreement — mean | **0.883** (0.883105) |
| Pixel agreement — max | 0.997 |
| Field-majority match with CDL 2024 | **19 of 20** |
| Model card reference (not our data) | aAcc 60.64 %, mIoU 0.4269 |

Query used (read-only):

```sql
SELECT count(*), min(agreement_with_cdl),
       percentile_cont(0.5) WITHIN GROUP (ORDER BY agreement_with_cdl),
       avg(agreement_with_cdl),
       sum((v.crop_pred = h.crop_name)::int)
FROM vision_result v
LEFT JOIN field_crop_history h ON h.field_id = v.field_id AND h.year = 2024;
-- 20 | 0.1931 | 0.93395 | 0.883105 | 19
```

## Per-field table

| field_id | county FIPS | Prithvi majority | CDL 2024 majority (share) | pixel agreement | majority match |
| --- | --- | --- | --- | --- | --- |
| 171825001292309 | 17113 | Soybeans | Soybeans (0.96) | 0.945 | yes |
| 171825006921423 | 17113 | Corn | Corn (1.00) | 0.997 | yes |
| 171825006923844 | 17113 | Corn | Corn (0.95) | 0.882 | yes |
| 191825000014952 | 19169 | Corn | Soybeans (0.93) | 0.193 | **no** |
| 191825001175247 | 19169 | Soybeans | Soybeans (0.89) | 0.924 | yes |
| 191825001176098 | 19169 | Soybeans | Soybeans (0.96) | 0.989 | yes |
| 191825001176345 | 19169 | Soybeans | Soybeans (0.93) | 0.971 | yes |
| 191825001176875 | 19169 | Soybeans | Soybeans (0.96) | 0.966 | yes |
| 191825001177094 | 19169 | Soybeans | Soybeans (0.98) | 0.985 | yes |
| 191825002945908 | 19169 | Soybeans | Soybeans (0.97) | 0.956 | yes |
| 191825003867870 | 19169 | Corn | Corn (0.99) | 0.980 | yes |
| 191825003868071 | 19169 | Corn | Corn (0.83) | 0.879 | yes |
| 191825003868102 | 19169 | Corn | Corn (0.97) | 0.932 | yes |
| 191825003868954 | 19169 | Corn | Corn (0.92) | 0.936 | yes |
| 191825003869023 | 19169 | Corn | Corn (0.95) | 0.825 | yes |
| 311825001242480 | 31109 | Corn | Corn (0.96) | 0.899 | yes |
| 311825002820374 | 31109 | Soybeans | Soybeans (0.87) | 0.866 | yes |
| 311825008109480 | 31109 | Soybeans | Soybeans (0.99) | 0.997 | yes |
| 391825000729943 | 39159 | Corn | Corn (0.88) | 0.676 | yes |
| 391825009407249 | 39159 | Corn | Corn (0.97) | 0.865 | yes |

The one mismatch (191825000014952, CDL 2024 Soybeans 0.93; 2023 and 2025 Corn) is a corn–soybean rotation field; the cause is not confirmed (미확인).

## Consistency with other documents

- `docs/submission/submission.md` and `docs/submission/slides/index.html` already say "19 of 20" and "mean pixel agreement 0.883" — consistent. Adding min/median is optional there; do not use any other number.
- Do not write "accuracy 88 %", "95 %" or "Prithvi is accurate". Prithvi is an auxiliary layer; CDL is the crop label of record.
