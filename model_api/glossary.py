"""Static glossary for S6 (definitions only; no data values)."""

from . import config

TERMS = [
    ("evapotranspiration", "증발산", "Evapotranspiration", "토양 증발과 식물 증산으로 땅에서 대기로 나가는 물의 양(mm).",
     "Water leaving the land by soil evaporation plus plant transpiration (mm).", config.FAO56_URL),
    ("reference_et", "기준 증발산(ET0)", "Reference evapotranspiration (ET0)", "잘 관리된 기준 잔디면의 증발산. FAO-56 Penman-Monteith로 계산.",
     "ET of a well-watered reference grass surface, computed with FAO-56 Penman-Monteith.", config.FAO56_URL),
    ("crop_coefficient", "작물계수(Kc)", "Crop coefficient (Kc)", "작물 증발산 = Kc × ET0. 작물·생육 단계마다 다르다.",
     "Crop ET = Kc x ET0; varies by crop and growth stage.", config.FAO56_URL),
    ("soil_moisture_anomaly", "토양수분 아노말리", "Soil moisture anomaly", "같은 칸의 평년 대비 토양수분 차이. SMAP은 수십 km 칸 값이다.",
     "Difference from the same cell's normal soil moisture. SMAP cells are tens of km wide.", config.DATA_SOURCE_URLS["SMAP"]),
    ("ndvi", "NDVI(식생지수)", "NDVI", "근적외·적색 반사로 계산한 녹색 식생 지표(무차원).",
     "Normalized difference vegetation index from near-infrared and red reflectance (dimensionless).", config.DATA_SOURCE_URLS["HLS"]),
    ("frost_risk", "서리 위험", "Frost risk", "최저기온이 0 °C 아래로 내려가는 날의 빈도.",
     "How often daily minimum temperature drops below 0 C.", None),
    ("water_balance", "물수지", "Water balance", "토양수분 = 이전 + 강수 − 증발산 − 유출 − 배수. 하루 단위 계산.",
     "Soil water = previous + rain - ET - runoff - drainage, computed daily.", config.FAO56_URL),
    ("cvar", "CVaR(조건부 위험값)", "CVaR", "몬테카를로 표본 중 가장 나쁜 10 %의 평균. 꼬리 위험(회복력) 지표.",
     "Mean of the worst 10 % of Monte Carlo samples: a tail-risk (resilience) measure.", None),
    ("monte_carlo", "몬테카를로", "Monte Carlo", "과거 기상 연도를 무작위로 다시 뽑아 여러 번 계산해 분포를 얻는 방법.",
     "Re-running the model on randomly resampled past weather years to get a distribution.", None),
    ("cover_crop", "피복작물", "Cover crop", "수확 뒤 맨땅을 덮으려고 심는 작물(예: 겨울 호밀).",
     "A crop grown to cover otherwise bare soil after harvest (e.g., winter cereal rye).", None),
    ("nitrogen_fixation", "질소 고정", "Nitrogen fixation", "콩과 작물(대두·알팔파)이 뿌리혹 세균으로 공기 중 질소를 쓰는 과정.",
     "Legumes (soybean, alfalfa) using root-nodule bacteria to take nitrogen from the air.", None),
    ("deep_rooted_crop", "심근 작물", "Deep-rooted crop", "뿌리가 깊게 내려 깊은 토양수분을 쓰는 작물(예: 알팔파).",
     "A crop whose roots reach deep soil water (e.g., alfalfa).", None),
    ("satellite_vs_ground", "위성 vs 지상 관측", "Satellite vs ground observation",
     "위성 값은 칸(수십 m–수십 km) 평균이다. 필지 안 차이는 현장 확인이 필요하다.",
     "Satellite values are cell averages (tens of m to tens of km); within-field differences need checking on the ground.", None),
    ("bare_period", "맨땅 기간", "Bare-soil period", "NDVI가 낮아 살아 있는 식생이 거의 없는 기간.",
     "A period with very little living vegetation (low NDVI).", None),
]


def glossary() -> dict:
    return {"terms": [{"term_id": t, "ko": ko, "en": en, "short_ko": sk, "short_en": se, "source_url": url}
                      for t, ko, en, sk, se, url in TERMS]}
