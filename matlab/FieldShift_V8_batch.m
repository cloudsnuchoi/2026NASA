%% ART FARM / Field Shift V8 offline batch (base MATLAB, no interaction).
% Run: matlab -batch "run('matlab/FieldShift_V8_batch.m')"
% Container paths are intentional; /data is mounted by the MATLAB runtime.
% One row per field/rotation; all numeric model outputs (including allocation,
% history and epoch vectors) are expanded into scalar CSV columns. Vector
% suffixes _1, _2, ... follow MATLAB linear order: history 2016:2025,
% shortTerm 2026:2028, epochs baseline/2026:2029/2030:2039,
% allocation Corn/Soy/Wheat, polygon vertices 1:4 then closing vertex 1.
% Terrain visualization grids and all map/plot/interactive code are omitted.
% Successful-path equations/rounding preserved from FieldShift_LiveAPI_Engineeee.m.
% Exceptions: fail closed on API errors/incomplete data instead of fabricated
% USGS elevation, POWER history/GWETROOT, NWS anomaly or climate replacements.
% These are screening estimates, NOT forecasts or calibrated probabilities.
% Coefficient provenance assessment (original file is the implementation source):
% - Kc 1.08/0.86/0.75: original cites FAO generically, without table/stage/page;
%   DIRECTIVE notes these differ from FAO-56 Table 12 midseason coefficients.
% - Ky 1.25/0.85/0.65: original FAO attribution has no crop-specific citation.
% - yields 200/62/80 bu/ac, prices 4.60/11.5/6.20 USD/bu, costs 680/450/310
%   USD/ac: original USDA ERS claim has no year/table/geography; unvalidated.
% - rotation/cover/runoff/erosion/N credit/storage/heat/NDVI and optimization
%   synergy coefficients, floors/caps and 60:40 future blend: unvalidated.
% - NDVI is a GWETROOT/water-ratio proxy, NOT observed satellite NDVI.
% - POWER ET0 formula is the original simplified radiation/temperature proxy,
%   NOT full FAO-56 Penman-Monteith; water/SOM are relative prototype indices.
% No new scientific-source claim or calibration is made by this batch copy.
% Files are diagnostic outputs only, not the fixed SOT DB ingestion tables.

inputFile = '/data/processed/v1/matlab/inputs/fields_20.csv';
outputDir = '/data/processed/v1/matlab/outputs/woochan';
outputFile = fullfile(outputDir, 'v8_cards_20fields.csv');
failureFile = fullfile(outputDir, 'v8_failures_20fields.csv');
if isfile(outputFile) || isfile(failureFile)
    error('FieldShift:OutputExists', 'Refusing to overwrite existing V8 batch outputs.');
end
if ~isfile(inputFile)
    error('FieldShift:InputMissing', 'Required input is missing: %s', inputFile);
end
inputOptions = detectImportOptions(inputFile, 'TextType', 'string');
inputOptions = setvartype(inputOptions, 'field_id', 'string');
fields = readtable(inputFile, inputOptions);
vertexNames = {'v1_lat','v1_lon','v2_lat','v2_lon', ...
               'v3_lat','v3_lon','v4_lat','v4_lon'};
requiredNames = [{'field_id'}, vertexNames];
if height(fields) ~= 20 || ~all(ismember(requiredNames, fields.Properties.VariableNames))
    error('FieldShift:InputSchema', 'Expected 20 fields with field_id and four lat/lon vertices.');
end
if any(ismissing(fields.field_id) | strlength(strtrim(fields.field_id)) == 0) || ...
        numel(unique(fields.field_id)) ~= height(fields)
    error('FieldShift:FieldIDs', 'field_id must be nonempty, unique strings.');
end
selectedCrops = {'Corn', 'Soybean', 'Wheat'};
rows = empty_card_table();
failures = table('Size', [0 5], ...
    'VariableTypes', {'string','double','string','string','string'}, ...
    'VariableNames', {'field_id','input_row','stage','error_id','message'});
for fieldIdx = 1:height(fields)
    fieldID = fields.field_id(fieldIdx);
    stage = "input";
    try
        vertices = fields{fieldIdx, vertexNames};
        if ~isnumeric(vertices) || any(~isfinite(vertices))
            error('FieldShift:Vertices', 'Vertices must be finite numeric latitude/longitude values.');
        end
        lat4 = vertices(1:2:end);
        lon4 = vertices(2:2:end);
        if any(abs(lat4) > 90) || any(abs(lon4) > 180) || ...
                size(unique([lat4(:), lon4(:)], 'rows'), 1) ~= 4
            error('FieldShift:Vertices', 'Four distinct valid WGS84 vertices are required.');
        end
        polyLat = [lat4, lat4(1)];
        polyLon = [lon4, lon4(1)];
        pinLat = mean(lat4); pinLon = mean(lon4);
        stage = "USGS";
        [geo, dem] = fetch_real_usgs_terrain_noaddon(pinLat, pinLon, polyLat, polyLon);
        if ~geo.isSupported
            error('FieldShift:Unsupported', '%s', geo.message);
        end
        if ~isfinite(geo.area_m2) || geo.area_m2 <= 0
            error('FieldShift:Area', 'Polygon area must be positive.');
        end
        stage = "POWER";
        env = fetch_live_nasa_power(pinLat, pinLon);
        stage = "NWS_OpenMeteo";
        proj = predict_future_climate_with_weather_agency(pinLat, pinLon, env);
        stage = "cards";
        cards = compute_fao_rotation_cards(selectedCrops, geo, dem, env, proj);
        stage = "allocation";
        optAlloc = optimize_crop_allocation_noaddon(selectedCrops, geo, dem, env, proj);
        stage = "export_validation";
        fieldRows = rows([],:);
        for cardIdx = 1:numel(cards)
            row = card_row(fieldID, fieldIdx, pinLat, pinLon, geo, dem, env, proj, cards(cardIdx), optAlloc);
            row = row(:, rows.Properties.VariableNames);
            numericColumns = varfun(@isnumeric, row, 'OutputFormat', 'uniform');
            if any(~isfinite(row{1, numericColumns}))
                error('FieldShift:NonfiniteOutput', 'Nonfinite model output; field omitted.');
            end
            fieldRows = [fieldRows; row]; %#ok<AGROW>
        end
        if height(fieldRows) ~= 4
            error('FieldShift:CardCount', 'The original three-crop V8 must emit four rotations.');
        end
        % Append only after the entire field succeeds (no partial field success).
        rows = [rows; fieldRows]; %#ok<AGROW>
        fprintf('[%d/20] %s: %d screening rows\n', fieldIdx, fieldID, height(fieldRows));
    catch cause
        failures(end+1,:) = {fieldID, fieldIdx, stage, string(cause.identifier), string(cause.message)}; %#ok<SAGROW>
        fprintf(2, '[%d/20] %s FAILED (%s): %s\n', fieldIdx, fieldID, stage, cause.message);
    end
end
if ~isfolder(outputDir)
    mkdir(outputDir);
end
writetable(rows, outputFile, 'Encoding', 'UTF-8');
writetable(failures, failureFile, 'Encoding', 'UTF-8');
fprintf('V8 batch: %d/20 fields succeeded, %d rows, %d failed fields. NOT forecast.\n', ...
    height(fields) - height(failures), height(rows), height(failures));
if ~isempty(failures)
    error('FieldShift:BatchFailures', '%d fields failed; inspect %s. Successful fields only in %s.', ...
        height(failures), failureFile, outputFile);
end

function row = card_row(fieldID, inputRow, lat, lon, geo, dem, env, proj, card, allocation)
    out = struct('field_id', string(fieldID), 'input_row', inputRow, ...
        'latitude', lat, 'longitude', lon, 'rotation', string(card.rotName), ...
        'result_label', "screening estimate", ...
        'future_label', "prototype deterministic future scores; NOT forecast; NOT probabilities", ...
        'assumptions', "economic/index/agronomic coefficients unvalidated; original V8 values", ...
        'index_reference', "water/SOM relative to V8 continuous-corn reference, NOT strategy A; not guarantees", ...
        'ndvi_label', "unvalidated GWETROOT/water-ratio proxy; NOT observed NDVI", ...
        'et0_label', "V8 simplified radiation/temperature proxy; NOT full FAO-56 Penman-Monteith", ...
        'local_review_risks', "Local soil testing and agronomic review required; no fertilizer prescription", ...
        'terrain_source', string(dem.sourceTag), 'history_source', string(env.sourceTag), ...
        'future_source', string(proj.sourceTag));
    out = append_numeric(out, geo, 'geo');
    out = append_numeric(out, dem, 'dem');
    out = append_numeric(out, env, 'env');
    out = append_numeric(out, proj, 'proj');
    out = append_numeric(out, card, 'card');
    out = append_numeric(out, allocation, 'allocation');
    row = struct2table(out);
end

function out = append_numeric(out, value, prefix)
    names = fieldnames(value);
    for k = 1:numel(names)
        name = names{k};
        item = value.(name);
        column = [prefix '_' name];
        if isstruct(item)
            out = append_numeric(out, item, column);
        elseif isnumeric(item) || islogical(item)
            for j = 1:numel(item)
                if isscalar(item)
                    key = column;
                else
                    key = sprintf('%s_%d', column, j);
                end
                out.(key) = double(item(j));
            end
        end
    end
end

function rows = empty_card_table()
    % NaNs describe column shapes only; this row is never written as data.
    geo = struct('isSupported', false, 'area_m2', NaN, 'perimeter_m', NaN, ...
        'localX_m', nan(1,5), 'localY_m', nan(1,5));
    dem = struct('sourceTag', "", 'minElev_m', NaN, 'medianElev_m', NaN, ...
        'maxElev_m', NaN, 'slope_pct', NaN, 'isLiveAPI', false);
    past = struct('temp_C', nan(10,1), 'precip_mm', nan(10,1), ...
        'evap_mm', nan(10,1), 'ndvi', nan(10,1), 'soilMoisture', nan(10,1));
    current = struct('temp_C', NaN, 'precip_mm', NaN, 'evap_mm', NaN, ...
        'ndvi', NaN, 'ndvi_pct', NaN, 'soilMoisture', NaN);
    env = struct('pastYears', nan(10,1), 'past', past, 'current', current, 'sourceTag', "");
    climate = struct('temp_C', nan(3,1), 'precip_mm', nan(3,1), 'evap_mm', nan(3,1));
    proj = struct('decadeTrendTemp_C', NaN, 'nwsTempAnomaly_C', NaN, ...
        'shortTermYears', nan(3,1), 'shortTerm', climate, 'epochs', climate, 'sourceTag', "");
    card = struct('rotName', "", 'resultNum', NaN, 'ETm_mm', NaN, 'netProfit_ac', NaN, ...
        'somFactor', NaN, 'ndviRaw', NaN, 'epochScores', nan(1,3), 'deficitPct', NaN, ...
        'nFix_kg', NaN, 'waterIdx', NaN, 'somIdx', NaN, 'waterDiff_pct', NaN, ...
        'somDiff_pct', NaN, 'profit_usd', NaN);
    allocation = struct('profitPerAcre_usd', NaN, 'ratios_pct', nan(1,3), ...
        'area_ha', nan(1,3), 'totalProfit_usd', NaN, 'waterUsed_mm', NaN, ...
        'waterLimit_mm', NaN, 'netNitrogen_kg_ha', NaN, ...
        'nitrogenLimit_kg_ha', NaN, 'nFixedCredit_kg_ha', NaN);
    row = card_row("", NaN, NaN, NaN, geo, dem, env, proj, card, allocation);
    rows = row([],:);
end

function tf = nws_fahrenheit(periods)
    if iscell(periods)
        tf = all(cellfun(@(p) strcmp(p.temperatureUnit, 'F'), periods));
    else
        tf = all(strcmp({periods.temperatureUnit}, 'F'));
    end
end

function [geo, dem] = fetch_real_usgs_terrain_noaddon(pinLat, pinLon, polyLat, polyLon)
    polyLat = reshape(polyLat, 1, []);
    polyLon = reshape(polyLon, 1, []);

    % 1) 미국 콘벨트 지원 권역 확인 (내장 inpolygon 사용)
    cbLat = [36.0, 36.0, 48.0, 48.0, 36.0];
    cbLon = [-104.0, -80.0, -80.0, -104.0, -104.0];
    geo.isSupported = inpolygon(pinLat, pinLon, cbLat, cbLon) && all(inpolygon(polyLat, polyLon, cbLat, cbLon));
    if ~geo.isSupported
        geo.message = '서비스 가능 지역이 아닙니다 (미국 콘벨트 위도 36~48N, 경도 104~80W 외부).';
        dem = struct(); return;
    end
    geo.message = '정상 지원 권역';

    % 2) [Mapping Toolbox 완벽 대체]: WGS84 지구 타원체 자오선·묘유선 곡률반경(Rm, Rn) 직접 계산!
    %    WGS84 장반경 a = 6378137.0 m, 이심률 제곱 e^2 = 0.00669437999014
    vLat = polyLat(1:end-1);
    vLon = polyLon(1:end-1);
    lat0 = deg2rad(mean(vLat));
    a_wgs84  = 6378137.0;
    e2_wgs84 = 0.00669437999014;
    denom    = sqrt(1 - e2_wgs84 * (sin(lat0)^2));
    Rm = a_wgs84 * (1 - e2_wgs84) / (denom^3); % 위도 방향 곡률반경 (m/rad)
    Rn = a_wgs84 / denom;                      % 경도 방향 곡률반경 (m/rad)

    mPerLat = Rm * (pi / 180);
    mPerLon = Rn * cos(lat0) * (pi / 180);

    x_m = reshape((polyLon - mean(vLon)) * mPerLon, 1, []);
    y_m = reshape((polyLat - mean(vLat)) * mPerLat, 1, []);

    % 가우스 신발끈 공식(내장 polyarea)으로 WGS84 타원체 투영 면적 및 둘레 정확히 산출
    geo.area_m2     = polyarea(x_m, y_m);
    geo.perimeter_m = sum(hypot(diff(x_m), diff(y_m)));
    geo.localX_m    = x_m;
    geo.localY_m    = y_m;

    % 3) USGS National Map 3DEP Elevation API 실시간 호출 (폴리곤 꼭짓점 실제 해발고도 조회)
    nVerts = numel(polyLat) - 1;
    opts = weboptions('Timeout', 8);
    elevList = zeros(1, nVerts);
    apiSuccess = true;
    try
        for k = 1:nVerts
            url = sprintf('https://epqs.nationalmap.gov/v1/json?x=%.6f&y=%.6f&wkid=4326&units=Meters', ...
                polyLon(k), polyLat(k));
            res = webread(url, opts);
            elevList(k) = str2double(string(res.value));
        end
        if any(~isfinite(elevList)) || any(elevList < -100)
            error('Invalid elevation returned');
        end
        dem.sourceTag = 'USGS 3DEP 실시간 API 수신 성공';
    catch cause
        error('FieldShift:USGSFailure', 'USGS elevation unavailable: %s', cause.message);
    end

    elevCol          = reshape(elevList, [], 1);
    dem.minElev_m    = min(elevCol);
    dem.medianElev_m = median(elevCol);
    dem.maxElev_m    = max(elevCol);

    dem.slope_pct = max(0.8, round(((dem.maxElev_m - dem.minElev_m) / max(1, sqrt(geo.area_m2))) * 100 * 1.8, 2));
    dem.isLiveAPI = apiSuccess;
end

function env = fetch_live_nasa_power(lat, lon)
    % NASA POWER API 호출 (2016-01-01 ~ 2025-12-31 과거 10년 실제 일별 관측 데이터)
    url = sprintf(['https://power.larc.nasa.gov/api/temporal/daily/point?' ...
        'parameters=T2M,T2M_MAX,T2M_MIN,PRECTOTCORR,ALLSKY_SFC_SW_DWN,GWETROOT' ...
        '&community=ag&longitude=%.4f&latitude=%.4f&start=20160101&end=20251231&format=JSON'], lon, lat);

    env.pastYears = (2016:2025)';
    nYrs = numel(env.pastYears);
    try
        raw = webread(url, weboptions('Timeout', 12));
        p = raw.properties.parameter;
        fNames = fieldnames(p.T2M); % 'x20160101' 형태

        nDays = numel(fNames);
        yrVec = zeros(nDays, 1);
        tMean = zeros(nDays, 1); tMax = zeros(nDays, 1); tMin = zeros(nDays, 1);
        prec  = zeros(nDays, 1); rad  = zeros(nDays, 1); gwet = zeros(nDays, 1);

        for i = 1:nDays
            fn = fNames{i};
            yrVec(i) = str2double(fn(2:5));
            tMean(i) = p.T2M.(fn);
            tMax(i)  = p.T2M_MAX.(fn);
            tMin(i)  = p.T2M_MIN.(fn);
            prec(i)  = p.PRECTOTCORR.(fn);
            rad(i)   = p.ALLSKY_SFC_SW_DWN.(fn);
            gwet(i)  = p.GWETROOT.(fn);
        end

        expectedDates = datetime(2016,1,1):datetime(2025,12,31);
        expectedKeys = cellstr("x" + string(expectedDates, 'yyyyMMdd'));
        if numel(fNames) ~= numel(expectedKeys) || ~all(ismember(expectedKeys, fNames)) || ...
                any(~isfinite([tMean; tMax; tMin; prec; rad; gwet])) || ...
                any(tMean <= -90 | tMax <= -90 | tMin <= -90 | tMax < tMin | ...
                    prec < 0 | rad < 0 | gwet < 0 | gwet > 1)
            error('FieldShift:POWERIncomplete', 'POWER daily series is incomplete or contains missing/invalid values.');
        end
        valid = (tMean > -90) & (prec >= 0);
        sw_safe = max(5.0, rad);
        et0_daily = max(0, 0.0023 * (sw_safe * 0.408) .* max(0, tMean + 17.8) .* sqrt(max(0, tMax - tMin)));

        for yIdx = 1:nYrs
            yr = env.pastYears(yIdx);
            mask = valid & (yrVec == yr);
            env.past.temp_C(yIdx, 1)    = round(mean(tMean(mask)), 2);
            env.past.precip_mm(yIdx, 1) = round(sum(prec(mask)), 1);
            env.past.evap_mm(yIdx, 1)   = round(sum(et0_daily(mask)), 1);

            meanGwet = mean(gwet(mask & gwet > 0));
            if ~isfinite(meanGwet)
                error('FieldShift:POWERSoilMoisture', 'No positive GWETROOT values for %d.', yr);
            end
            wRatio = min(1.25, env.past.precip_mm(yIdx) / max(400, env.past.evap_mm(yIdx)));
            env.past.ndvi(yIdx, 1) = round(min(0.88, max(0.48, 0.42 + 0.32 * meanGwet + 0.14 * wRatio)), 3);
            env.past.soilMoisture(yIdx, 1) = round(meanGwet, 3);
        end
        env.sourceTag = sprintf('NASA POWER 과거 10년(2016~2025) 실측 수신 완료 (%.4f, %.4f)', lat, lon);
    catch cause
        error('FieldShift:POWERFailure', 'NASA POWER unavailable: %s', cause.message);
    end

    env.current.temp_C       = round(mean(env.past.temp_C), 1);
    env.current.precip_mm    = round(mean(env.past.precip_mm), 0);
    env.current.evap_mm      = round(mean(env.past.evap_mm), 0);
    env.current.ndvi         = round(mean(env.past.ndvi), 2);
    env.current.ndvi_pct     = round(env.current.ndvi * 100, 1);
    env.current.soilMoisture = round(mean(env.past.soilMoisture), 2);
end

function proj = predict_future_climate_with_weather_agency(lat, lon, env)
    % Prototype deterministic extrapolation/blend; NOT a forecast or distribution.
    % Open-Meteo MRI_AGCM3_2_S is not NOAA GFS or NASA NEX-GDDP-CMIP6.
    % 1단계: 과거 10년 실측 시계열 선형 회귀(polyfit) 추세 계산
    pastYrs = reshape(env.pastYears, [], 1);
    pTemp   = polyfit(pastYrs, reshape(env.past.temp_C, [], 1), 1);
    pPrec   = polyfit(pastYrs, reshape(env.past.precip_mm, [], 1), 1);
    pEvap   = polyfit(pastYrs, reshape(env.past.evap_mm, [], 1), 1);

    % 10년당 기온 상승 추세 기울기 (과거 데이터 기반, 물리적 상하한 캡 적용)
    slopeTempPerYr = min(0.08, max(0.015, pTemp(1)));
    slopePrecPerYr = min(4.0,  max(-6.0,  pPrec(1)));
    slopeEvapPerYr = min(6.5,  max(1.5,   pEvap(1)));
    proj.decadeTrendTemp_C = round(slopeTempPerYr * 10, 2);

    % 2단계: 미국 기상청(NOAA National Weather Service) 공식 API 실시간 호출
    nwsAnomaly_C = 0.0;
    try
        optsNWS = weboptions('Timeout', 8, 'UserAgent', 'FieldShift_AgriEngine_MATLAB/1.0');
        ptUrl = sprintf('https://api.weather.gov/points/%.4f,%.4f', lat, lon);
        ptMeta = webread(ptUrl, optsNWS);
        fcUrl = string(ptMeta.properties.forecast);
        fcData = webread(fcUrl, optsNWS);
        periods = fcData.properties.periods;
        if isstruct(periods)
            tempsF = [periods.temperature];
        elseif iscell(periods)
            tempsF = cellfun(@(x) x.temperature, periods);
        else
            error('FieldShift:NWSInvalid', 'Invalid NWS forecast periods.');
        end
        if isempty(tempsF) || any(~isfinite(tempsF)) || ...
                ~nws_fahrenheit(periods)
            error('FieldShift:NWSInvalid', 'NWS temperatures must be finite and in Fahrenheit.');
        end
        meanForecast_C = (mean(tempsF) - 32) * 5 / 9;
        % 기상청 단기 예보 기온과 평년 기온 간 편차(Anomaly)를 보정 계수로 산출
        nwsAnomaly_C = min(1.2, max(-1.2, (meanForecast_C - env.current.temp_C) * 0.08));
    catch cause
        error('FieldShift:NWSFailure', 'NWS unavailable: %s', cause.message);
    end
    proj.nwsTempAnomaly_C = round(nwsAnomaly_C, 2);

    % V8 deterministic blend with Open-Meteo MRI_AGCM3_2_S; NOT a forecast.
    url = sprintf(['https://climate-api.open-meteo.com/v1/climate?' ...
        'latitude=%.4f&longitude=%.4f&start_date=2026-01-01&end_date=2039-12-31' ...
        '&models=MRI_AGCM3_2_S&daily=temperature_2m_mean,precipitation_sum,et0_fao_evapotranspiration'], lat, lon);

    proj.shortTermYears = (2026:2028)';
    try
        raw = webread(url, weboptions('Timeout', 12));
        timeCells = raw.daily.time;
        tVec  = raw.daily.temperature_2m_mean;
        pVec  = raw.daily.precipitation_sum;
        etVec = raw.daily.et0_fao_evapotranspiration;
        yrs = cellfun(@(s) str2double(s(1:4)), timeCells);

        expectedDates = datetime(2026,1,1):datetime(2039,12,31);
        expectedTimes = cellstr(string(expectedDates, 'yyyy-MM-dd'));
        if numel(timeCells) ~= numel(expectedTimes) || ...
                ~all(ismember(expectedTimes, timeCells)) || ...
                numel(tVec) ~= numel(timeCells) || numel(pVec) ~= numel(timeCells) || ...
                numel(etVec) ~= numel(timeCells) || ...
                any(~isfinite([tVec(:); pVec(:); etVec(:)])) || ...
                any(pVec(:) < 0) || any(etVec(:) < 0)
            error('FieldShift:ClimateIncomplete', 'Open-Meteo daily series is incomplete or invalid.');
        end

        for k = 1:3
            yr = proj.shortTermYears(k);
            yMask = (yrs == yr);
            modelT = mean(tVec(yMask), 'omitnan');
            trendT = env.current.temp_C + slopeTempPerYr * (yr - 2023) + nwsAnomaly_C;
            proj.shortTerm.temp_C(k,1) = round(0.6 * modelT + 0.4 * trendT, 2);

            modelP = sum(pVec(yMask), 'omitnan');
            trendP = env.current.precip_mm + slopePrecPerYr * (yr - 2023);
            proj.shortTerm.precip_mm(k,1) = round(0.6 * modelP + 0.4 * trendP, 1);

            modelE = sum(etVec(yMask), 'omitnan');
            trendE = env.current.evap_mm + slopeEvapPerYr * (yr - 2023);
            proj.shortTerm.evap_mm(k,1) = round(0.6 * modelE + 0.4 * trendE, 1);
        end

        % 단기(2026~2029) 및 2030년대(2030~2039) 예측 산출
        m20s = (yrs >= 2026) & (yrs <= 2029);
        m30s = (yrs >= 2030) & (yrs <= 2039);

        t20s = round(0.6 * mean(tVec(m20s), 'omitnan') + 0.4 * (env.current.temp_C + slopeTempPerYr * 4.5 + nwsAnomaly_C), 1);
        t30s = round(0.6 * mean(tVec(m30s), 'omitnan') + 0.4 * (env.current.temp_C + slopeTempPerYr * 12.0 + nwsAnomaly_C), 1);
        p20s = round(0.6 * (sum(pVec(m20s), 'omitnan') / 4)  + 0.4 * (env.current.precip_mm + slopePrecPerYr * 4.5), 0);
        p30s = round(0.6 * (sum(pVec(m30s), 'omitnan') / 10) + 0.4 * (env.current.precip_mm + slopePrecPerYr * 12.0), 0);
        e20s = round(0.6 * (sum(etVec(m20s), 'omitnan') / 4)  + 0.4 * (env.current.evap_mm + slopeEvapPerYr * 4.5), 0);
        e30s = round(0.6 * (sum(etVec(m30s), 'omitnan') / 10) + 0.4 * (env.current.evap_mm + slopeEvapPerYr * 12.0), 0);

        proj.epochs.names     = {'2016-2025 baseline', '2026-2029 prototype NOT forecast', '2030-2039 prototype NOT forecast'};
        proj.epochs.temp_C    = [env.current.temp_C, t20s, t30s];
        proj.epochs.precip_mm = [env.current.precip_mm, p20s, p30s];
        proj.epochs.evap_mm   = [env.current.evap_mm, e20s, e30s];
        proj.sourceTag = 'Prototype deterministic blend: POWER trend + NWS short-term anomaly + Open-Meteo MRI_AGCM3_2_S; NOT forecast';
    catch cause
        error('FieldShift:ClimateFailure', 'Open-Meteo climate data unavailable: %s', cause.message);
    end
end

function cards = compute_fao_rotation_cards(selectedCrops, geo, dem, env, proj)
    % =========================================================================
    % [윤작 생성 규칙]:
    %   1) 1가지 선택은 삭제됨 (최소 2가지 이상)
    %   2) 동일 작물이 연속으로 나오면 안 됨 (예: 옥수수->옥수수->콩 X, 옥수수->콩->옥수수 O)
    %   3) 2가지 선택 시에는 2단계만 사용 (예: 옥수수->콩 O, 콩->옥수수 O, 옥수수->콩->옥수수 X)
    %   4) 순위를 매기지 않고 [1번 결과], [2번 결과]... 순서대로 산출
    % =========================================================================

    normCrops = cell(size(selectedCrops));
    korNames  = containers.Map({'Corn','Soy','Wheat'}, {'옥수수','콩','밀'});
    for k = 1:numel(selectedCrops)
        cName = char(selectedCrops{k});
        if strcmpi(cName, 'Soybean') || strcmpi(cName, 'Soy') || strcmp(cName, '대두/콩') || strcmp(cName, '콩')
            normCrops{k} = 'Soy';
        elseif strcmpi(cName, 'Wheat') || strcmp(cName, '밀')
            normCrops{k} = 'Wheat';
        else
            normCrops{k} = 'Corn';
        end
    end
    normCrops = unique(normCrops, 'stable');

    if numel(normCrops) < 2
        error('1가지 작물만 선택하는 방식은 지원하지 않습니다. 최소 2가지 작물을 선택하세요.');
    end

    % V8 coefficients preserved verbatim; specific FAO/USDA table/year sources unverified.
    db.Corn  = struct('kc',1.08, 'ky',1.25, 'baseYield',200, 'price',4.60, 'cost',680, 'c_in',1.00, 'nFix',0);
    db.Soy   = struct('kc',0.86, 'ky',0.85, 'baseYield',62,  'price',11.5, 'cost',450, 'c_in',1.08, 'nFix',65);
    db.Wheat = struct('kc',0.75, 'ky',0.65, 'baseYield',80,  'price',6.20, 'cost',310, 'c_in',1.22, 'nFix',15);

    % 2) 선택된 작물 개수(2가지 vs 3가지)에 맞춰 유효한 윤작 시퀀스 동적 구성
    defs = [];
    if numel(normCrops) == 2
        c1 = normCrops{1};
        c2 = normCrops{2};
        seqList = { {c1, c2}, {c2, c1} };
        titleList = {'교호 윤작 시나리오 1', '교호 윤작 시나리오 2'};
        for s = 1:numel(seqList)
            sq = seqList{s};
            if ~has_consecutive_duplicate(sq)
                rName = sprintf('%s → %s', korNames(sq{1}), korNames(sq{2}));
                defs = [defs; struct('resultNum', numel(defs)+1, 'title', titleList{s}, ...
                    'rotName', rName, 'seq', {sq}, 'hasCover', ismember('Wheat', sq), 'rotBump', 1.09)]; %#ok<AGROW>
            end
        end
    else
        candidateSeqs = {
            {'Corn', 'Soy', 'Wheat'}, '물 절약·균형 윤작',      false, 1.11;
            {'Soy', 'Wheat', 'Corn'}, '질소 고정·토양 재생 윤작', true,  1.10;
            {'Wheat', 'Corn', 'Soy'}, '수분 방어·표토 보전 윤작', true,  1.10;
            {'Corn', 'Soy', 'Corn'},  '수익 집중 교호 윤작',      false, 1.08
        };
        for s = 1:size(candidateSeqs, 1)
            sq = candidateSeqs{s, 1};
            if ~has_consecutive_duplicate(sq) && all(ismember(sq, normCrops))
                rName = sprintf('%s → %s → %s', korNames(sq{1}), korNames(sq{2}), korNames(sq{3}));
                defs = [defs; struct('resultNum', numel(defs)+1, 'title', candidateSeqs{s, 2}, ...
                    'rotName', rName, 'seq', {sq}, 'hasCover', candidateSeqs{s, 3}, 'rotBump', candidateSeqs{s, 4})]; %#ok<AGROW>
            end
        end
    end

    runoffLossRatio = 0.12 + 0.015 * dem.slope_pct;
    P_eff_mm = mean(proj.shortTerm.precip_mm) * (1 - runoffLossRatio);
    ET0_mm   = mean(proj.shortTerm.evap_mm);
    acres    = geo.area_m2 * 0.000247105;

    refET_mm  = db.Corn.kc * ET0_mm;
    refSOM    = db.Corn.c_in * (1 - 0.06 * dem.slope_pct);

    nCards = numel(defs);
    cards = repmat(struct(), nCards, 1);

    for i = 1:nCards
        d = defs(i);
        seq = d.seq;
        meanKc   = mean(cellfun(@(x) db.(x).kc, seq));
        meanKy   = mean(cellfun(@(x) db.(x).ky, seq));
        meanCin  = mean(cellfun(@(x) db.(x).c_in, seq));
        meanNFix = mean(cellfun(@(x) db.(x).nFix, seq));

        mulchEvapReduction = 0.06 * d.hasCover + 0.05 * (numel(unique(seq)) - 1);
        actual_Kc = meanKc * (1 - mulchEvapReduction);
        ETm_mm = actual_Kc * ET0_mm;

        soilStorage_mm = 160 * env.current.soilMoisture * (1 + 0.08 * d.hasCover);
        waterSupply_mm = min(ETm_mm, P_eff_mm + soilStorage_mm);
        waterDeficitRatio = max(0, 1 - (waterSupply_mm / ETm_mm));

        dT_stress = max(0, mean(proj.shortTerm.temp_C) - env.current.temp_C);
        heatPenalty = 0.035 * dT_stress * (meanKy / 1.0);

        yieldMultiplier = max(0.45, (1 - meanKy * waterDeficitRatio - heatPenalty) * d.rotBump);

        baseRev_ac  = mean(cellfun(@(x) db.(x).baseYield * db.(x).price, seq));
        baseCost_ac = mean(cellfun(@(x) db.(x).cost, seq)) + (d.hasCover * 35) - (meanNFix * 0.85);
        netProfit_ac = max(40, baseRev_ac * yieldMultiplier - baseCost_ac);

        erosionLoss = 0.06 * dem.slope_pct * (1 - 0.55 * d.hasCover - 0.25 * (numel(unique(seq)) > 1));
        somFactor = (meanCin + 0.18 * d.hasCover) * (1 - erosionLoss);

        epScores = zeros(1, 3);
        for eIdx = 1:3
            eP_eff = proj.epochs.precip_mm(eIdx) * (1 - runoffLossRatio);
            eETm   = actual_Kc * proj.epochs.evap_mm(eIdx);
            eDef   = max(0, 1 - min(1, (eP_eff + soilStorage_mm) / eETm));
            eHeat  = max(0, proj.epochs.temp_C(eIdx) - env.current.temp_C) * 0.04 * meanKy;
            epScores(eIdx) = round(100 * max(0.35, (1 - meanKy * eDef - eHeat) * d.rotBump), 1);
        end

        cards(i).resultNum      = d.resultNum;
        cards(i).label          = sprintf('%d번 결과', d.resultNum);
        cards(i).title          = d.title;
        cards(i).rotName        = d.rotName;
        cards(i).ETm_mm         = round(ETm_mm, 1);
        cards(i).netProfit_ac   = round(netProfit_ac, 1);
        cards(i).somFactor      = somFactor;
        cards(i).ndviRaw        = round(min(0.92, env.current.ndvi * yieldMultiplier), 2);
        cards(i).epochScores    = epScores;
        cards(i).deficitPct     = round(waterDeficitRatio * 100, 1);
        cards(i).nFix_kg        = round(meanNFix);

        cards(i).waterIdx       = round((ETm_mm / refET_mm) * 100, 1);
        cards(i).somIdx         = round((somFactor / refSOM) * 100, 1);
        cards(i).waterDiff_pct  = round(cards(i).waterIdx - 100, 1);
        cards(i).somDiff_pct    = round(cards(i).somIdx - 100, 1);
        cards(i).profit_usd     = round(acres * netProfit_ac);

        cards(i).pros = 'Screening estimate; unvalidated prototype assumptions.';
        cards(i).cons = 'Deterministic future scores are NOT forecasts, probabilities, or yield guarantees.';
        cards(i).prescription = 'Local soil testing and agronomic review required; no fertilizer prescription.';
    end
end

function tf = has_consecutive_duplicate(seq)
    tf = false;
    for idx = 1:(numel(seq) - 1)
        if strcmpi(seq{idx}, seq{idx+1})
            tf = true;
            return;
        end
    end
end

function optAlloc = optimize_crop_allocation_noaddon(selectedCrops, geo, dem, env, proj)
    % =========================================================================
    % [Optimization Toolbox 완벽 대체]:
    %   외부 애드온(fmincon / linprog) 없이 순수 기본 MATLAB 내장 함수인
    %   fminsearch(Nelder-Mead 비선형 탐색) + 심플렉스 제약 투영(Simplex Projection) 및
    %   라그랑주 페널티 결합 알고리즘으로 물·비료 한도 내 최대 수익 작물 비율을 정밀 계산합니다.
    % =========================================================================
    acres = geo.area_m2 * 0.000247105;
    total_ha = geo.area_m2 / 10000;

    runoffLossRatio = 0.12 + 0.015 * dem.slope_pct;
    P_eff_mm = mean(proj.shortTerm.precip_mm) * (1 - runoffLossRatio);
    ET0_mm   = mean(proj.shortTerm.evap_mm);
    soilStorage_mm = 160 * env.current.soilMoisture;
    availWater_mm  = P_eff_mm + soilStorage_mm;

    allNames = {'Corn', 'Soy', 'Wheat'};
    korMap   = containers.Map({'Corn','Soy','Wheat'}, {'옥수수(Corn)','대두/콩(Soybean)','밀(Wheat)'});
    kcMap    = containers.Map(allNames, [1.08, 0.86, 0.75]);
    kyMap    = containers.Map(allNames, [1.25, 0.85, 0.65]);
    revMap   = containers.Map(allNames, [200*4.60, 62*11.50, 80*6.20]);
    costMap  = containers.Map(allNames, [680, 450, 310]);
    nReqMap  = containers.Map(allNames, [185, -55, 90]);

    normCrops = cell(size(selectedCrops));
    for k = 1:numel(selectedCrops)
        cName = char(selectedCrops{k});
        if strcmpi(cName, 'Soybean') || strcmpi(cName, 'Soy') || strcmp(cName, '대두/콩') || strcmp(cName, '콩')
            normCrops{k} = 'Soy';
        elseif strcmpi(cName, 'Wheat') || strcmp(cName, '밀')
            normCrops{k} = 'Wheat';
        else
            normCrops{k} = 'Corn';
        end
    end
    normCrops = unique(normCrops, 'stable');
    nC = numel(normCrops);

    kcVec   = zeros(nC, 1);
    kyVec   = zeros(nC, 1);
    revVec  = zeros(nC, 1);
    costVec = zeros(nC, 1);
    nReqVec = zeros(nC, 1);
    for k = 1:nC
        ck = normCrops{k};
        kcVec(k)   = kcMap(ck);
        kyVec(k)   = kyMap(ck);
        revVec(k)  = revMap(ck);
        costVec(k) = costMap(ck);
        nReqVec(k) = nReqMap(ck);
    end

    ETmVec = kcVec * ET0_mm;
    dT_stress = max(0, mean(proj.shortTerm.temp_C) - env.current.temp_C);
    baseNetProfitVec = zeros(nC, 1);
    for k = 1:nC
        defRatio = max(0, 1 - min(1, availWater_mm / ETmVec(k)));
        heatPen  = 0.035 * dT_stress * kyVec(k);
        yMult    = max(0.45, 1 - kyVec(k) * defRatio - heatPen);
        baseNetProfitVec(k) = max(40, revVec(k) * yMult - costVec(k));
    end

    cornRefET_mm        = 1.08 * ET0_mm;
    waterLimit_mm       = min(cornRefET_mm * 0.90, max(availWater_mm * 1.05, mean(ETmVec) * 1.02));
    nitrogenLimit_kg_ha = 110.0;

    if nC == 2
        lb = [0.30; 0.30];
        ub = [0.70; 0.70];
    else
        maxCornShare = max(0.40, min(0.60, 0.62 - 0.03 * dem.slope_pct));
        lb = [0.20; 0.20; 0.15];
        ub = [maxCornShare; 0.60; 0.50];
    end

    A = [reshape(ETmVec, 1, []); reshape(nReqVec, 1, [])];
    b = [waterLimit_mm; nitrogenLimit_kg_ha];

    synergyProfitFn = @(x) -( ...
        sum(baseNetProfitVec .* reshape(x, [], 1)) ...
        + 65.0 * (1 - sum(reshape(x, [], 1).^2)) ...
        + 35.0 * prod(x(1:min(2,end))) ...
    );

    % 1단계: 고밀도 심플렉스 격자 탐색으로 제약 조건을 완벽히 만족하는 초기 최적점(xInit) 확보
    bestVal = inf;
    xInit = ones(nC, 1) / nC;
    if nC == 2
        for r1 = linspace(lb(1), ub(1), 501)
            xCand = [r1; 1 - r1];
            if all(xCand >= lb) && all(xCand <= ub) && all(A * xCand <= b + 1e-6)
                val = synergyProfitFn(xCand);
                if val < bestVal, bestVal = val; xInit = xCand; end
            end
        end
    else
        for r1 = linspace(lb(1), ub(1), 201)
            for r2 = linspace(lb(2), min(ub(2), 1 - r1 - lb(3)), 201)
                r3 = 1 - r1 - r2;
                if r3 >= lb(3) && r3 <= ub(3)
                    xCand = [r1; r2; r3];
                    if all(A * xCand <= b + 1e-6)
                        val = synergyProfitFn(xCand);
                        if val < bestVal, bestVal = val; xInit = xCand; end
                    end
                end
            end
        end
    end

    % 2단계: 기본 MATLAB 내장 fminsearch(Nelder-Mead) + 제약 장벽(Barrier Penalty)으로 소수점 정밀 수렴
    penaltyObj = @(u) eval_constrained_simplex(u, lb, ub, A, b, synergyProfitFn);
    optsNM = optimset('Display', 'off', 'TolX', 1e-7, 'TolFun', 1e-7, 'MaxIter', 1500);
    uInit  = xInit(1:end-1);
    uOpt   = fminsearch(penaltyObj, uInit, optsNM);
    xOpt   = [uOpt(:); 1 - sum(uOpt(:))];

    % 만약 수치 오차로 경계를 살짝 벗어난 경우 안전한 심플렉스 해(xInit)로 보정
    if any(xOpt < lb - 1e-4) || any(xOpt > ub + 1e-4) || any(A * xOpt > b + 1e-3)
        xOpt = xInit;
    end

    % Reject the original solver's infeasible-initial-point edge case.
    if any(~isfinite(xOpt)) || any(xOpt < lb - 1e-4) || ...
            any(xOpt > ub + 1e-4) || any(A * xOpt > b + 1e-3)
        error('FieldShift:AllocationInfeasible', 'V8 solver did not produce a feasible allocation.');
    end

    xOptCol                      = reshape(xOpt, [], 1);
    optAlloc.solverName          = '순수 기본 MATLAB 내장 솔버 (fminsearch Nelder-Mead + KKT 심플렉스 투영)';
    optAlloc.profitPerAcre_usd   = -synergyProfitFn(xOptCol);
    optAlloc.cropNames           = normCrops;
    optAlloc.ratios_pct          = round(reshape(xOptCol, 1, []) * 100, 1);
    optAlloc.area_ha             = round(reshape(xOptCol, 1, []) * total_ha, 2);
    optAlloc.totalProfit_usd     = round(optAlloc.profitPerAcre_usd * acres);
    optAlloc.waterUsed_mm        = round(sum(ETmVec .* xOptCol), 1);
    optAlloc.waterLimit_mm       = round(waterLimit_mm, 1);
    optAlloc.netNitrogen_kg_ha   = round(sum(nReqVec .* xOptCol), 1);
    optAlloc.nitrogenLimit_kg_ha = round(nitrogenLimit_kg_ha, 1);

    soyIdx = find(strcmp(normCrops, 'Soy'), 1);
    if ~isempty(soyIdx)
        optAlloc.nFixedCredit_kg_ha = round(55 * xOptCol(soyIdx), 1);
    else
        optAlloc.nFixedCredit_kg_ha = 0.0;
    end

    parts = cell(1, nC);
    for k = 1:nC
        parts{k} = sprintf('%s %.1f%% (%.1f ha)', korMap(normCrops{k}), optAlloc.ratios_pct(k), optAlloc.area_ha(k));
    end
    optAlloc.summaryText = strjoin(parts, ' | ');
end

function val = eval_constrained_simplex(u, lb, ub, A, b, objFn)
    x = [u(:); 1 - sum(u(:))];
    violBounds = sum(max(0, lb - x).^2) + sum(max(0, x - ub).^2);
    violLinear = sum(max(0, A * x - b).^2);
    if violBounds > 0 || violLinear > 0
        val = objFn(min(ub, max(lb, x))) + 1e6 * (violBounds + violLinear);
    else
        val = objFn(x);
    end
end
