% woochan_kc_sensitivity: Kc -10%/0/+10% sensitivity of V8 May-Sep dekadal water deficit per field and rotation (cached POWER only).
% Offline, base MATLAB, no interaction, no network. Inputs (all produced/cached by FieldShift_V8_batch):
%   /data/processed/v1/matlab/outputs/woochan/v8_cards_20fields.csv  (field_id, card_resultNum, rotation, dem_slope_pct)
%   /data/processed/v1/matlab/inputs/v8_api_cache/<field_id>/power.json (NASA POWER daily 2016-2025)
% Method (minimal FAO-56 style re-implementation of the V8 water part):
%   - ET0 daily = V8 simplified radiation/temperature proxy (NOT Penman-Monteith), same formula as V8.
%   - V8 uses ONE seasonal Kc per crop (Corn 1.08, Soy 0.86, Wheat 0.75); it has NO ini/mid/end
%     stages or stage lengths, so the single Kc is scaled (equivalent to scaling ini/mid/end alike).
%   - Rotation Kc = mean crop Kc x (1 - mulchEvapReduction), as in V8 compute_fao_rotation_cards.
%   - Peff = P x (1 - (0.12 + 0.015*slope_pct)), the V8 runoff loss.
%   - Season = May 1 - Sep 30; dekad deficit = max(0, Kc*ET0_dekad - Peff_dekad);
%     season deficit = sum over dekads, averaged over 2016-2025 (mm).
%   (The V8 annual balance incl. soil storage gives 0 deficit for every field, so it cannot show sensitivity.)
% Outputs: outputs/woochan/kc_sensitivity.csv, kc_sensitivity.png (previous copies moved to old/<stamp>/).

kcsCardsFile = '/data/processed/v1/matlab/outputs/woochan/v8_cards_20fields.csv';
kcsCacheRoot = '/data/processed/v1/matlab/inputs/v8_api_cache';
kcsOutDir = '/data/processed/v1/matlab/outputs/woochan';
kcsCsv = fullfile(kcsOutDir, 'kc_sensitivity.csv');
kcsPng = fullfile(kcsOutDir, 'kc_sensitivity.png');
kcsScales = [0.9, 1.0, 1.1];

if ~isfile(kcsCardsFile)
    error('KcSens:InputMissing', 'Missing %s (run FieldShift_V8_batch first).', kcsCardsFile);
end
kcsOpts = detectImportOptions(kcsCardsFile, 'TextType', 'string');
kcsOpts = setvartype(kcsOpts, {'field_id', 'rotation'}, 'string');
kcsCards = readtable(kcsCardsFile, kcsOpts);
kcsNeed = {'field_id', 'card_resultNum', 'rotation', 'dem_slope_pct'};
if ~all(ismember(kcsNeed, kcsCards.Properties.VariableNames))
    error('KcSens:Schema', 'v8_cards_20fields.csv lacks one of: %s', strjoin(kcsNeed, ', '));
end

% V8 three-crop rotation definitions (same order as V8 candidateSeqs -> card_resultNum 1..4).
kcsKc = struct('Corn', 1.08, 'Soy', 0.86, 'Wheat', 0.75);
kcsSeqs = {{'Corn','Soy','Wheat'}, {'Soy','Wheat','Corn'}, {'Wheat','Corn','Soy'}, {'Corn','Soy','Corn'}};
kcsCover = [false, true, true, false];
kcsRotKc = zeros(1, 4);
for kcsI = 1:4
    kcsSq = kcsSeqs{kcsI};
    kcsMean = mean(cellfun(@(x) kcsKc.(x), kcsSq));
    kcsMulch = 0.06 * kcsCover(kcsI) + 0.05 * (numel(unique(kcsSq)) - 1);
    kcsRotKc(kcsI) = kcsMean * (1 - kcsMulch);
end

kcsFields = unique(kcsCards.field_id, 'stable');
kcsRows = table('Size', [0 8], ...
    'VariableTypes', {'string','string','double','double','double','double','double','logical'}, ...
    'VariableNames', {'field_id','scenario','deficit_m10','deficit_0','deficit_p10', ...
                      'pct_change_m10','pct_change_p10','rank_changed'});
for kcsF = 1:numel(kcsFields)
    kcsFid = kcsFields(kcsF);
    kcsSub = kcsCards(kcsCards.field_id == kcsFid, :);
    kcsSub = sortrows(kcsSub, 'card_resultNum');
    if height(kcsSub) ~= 4 || ~isequal(kcsSub.card_resultNum(:)', 1:4)
        error('KcSens:Rotations', 'Field %s: expected card_resultNum 1..4.', kcsFid);
    end
    kcsPowerFile = fullfile(kcsCacheRoot, char(kcsFid), 'power.json');
    if ~isfile(kcsPowerFile)
        error('KcSens:CacheMissing', 'Missing cached POWER file %s (no network calls by design).', kcsPowerFile);
    end
    [kcsEt0, kcsPrec, kcsKey] = kcs_power_daily(kcsPowerFile);
    kcsPeff = kcsPrec * (1 - (0.12 + 0.015 * kcsSub.dem_slope_pct(1)));
    kcsDef = zeros(4, 3);
    for kcsR = 1:4
        for kcsS = 1:3
            kcsDef(kcsR, kcsS) = kcs_season_deficit(kcsScales(kcsS) * kcsRotKc(kcsR), kcsEt0, kcsPeff, kcsKey);
        end
    end
    kcsRank = zeros(4, 3);
    for kcsS = 1:3
        [~, kcsOrd] = sortrows([round(kcsDef(:, kcsS), 6), (1:4)']);
        kcsRank(kcsOrd, kcsS) = (1:4)';
    end
    kcsChanged = ~isequal(kcsRank(:, 1), kcsRank(:, 2)) || ~isequal(kcsRank(:, 3), kcsRank(:, 2));
    for kcsR = 1:4
        kcsBase = kcsDef(kcsR, 2);
        if kcsBase > 0
            kcsPm = 100 * (kcsDef(kcsR, 1) - kcsBase) / kcsBase;
            kcsPp = 100 * (kcsDef(kcsR, 3) - kcsBase) / kcsBase;
        else
            kcsPm = NaN; kcsPp = NaN;
        end
        kcsRows(end+1, :) = {kcsFid, kcsSub.rotation(kcsR), round(kcsDef(kcsR,1),2), round(kcsDef(kcsR,2),2), ...
            round(kcsDef(kcsR,3),2), round(kcsPm,2), round(kcsPp,2), kcsChanged}; %#ok<SAGROW>
    end
    fprintf('[%d/%d] %s deficit_0 = %s mm, rank_changed = %d\n', kcsF, numel(kcsFields), kcsFid, ...
        mat2str(round(kcsDef(:,2)', 1)), kcsChanged);
end

% Figure: per field, min/max % change across rotations for -10% and +10% (tornado-style).
kcsFig = figure('Visible', 'off', 'Position', [100 100 1100 750]);
kcsCleanup = onCleanup(@() close(kcsFig));
kcsN = numel(kcsFields);
kcsLo = zeros(kcsN, 1); kcsHi = zeros(kcsN, 1);
for kcsF = 1:kcsN
    kcsM = kcsRows.field_id == kcsFields(kcsF);
    kcsLo(kcsF) = mean(kcsRows.pct_change_m10(kcsM), 'omitnan');
    kcsHi(kcsF) = mean(kcsRows.pct_change_p10(kcsM), 'omitnan');
end
kcsAx = axes(kcsFig);
barh(kcsAx, 1:kcsN, kcsLo, 'FaceColor', [0.30 0.55 0.80]);
hold(kcsAx, 'on');
barh(kcsAx, 1:kcsN, kcsHi, 'FaceColor', [0.85 0.45 0.25]);
hold(kcsAx, 'off');
kcsAx.YTick = 1:kcsN;
kcsAx.YTickLabel = cellstr(kcsFields);
kcsAx.YDir = 'reverse';
xlabel(kcsAx, 'Change in May-Sep season water deficit vs Kc x1.0 (%, mean of 4 V8 rotations)');
title(kcsAx, sprintf('Kc sensitivity (-10%% blue, +10%% orange); ranking changed on %d/%d fields', ...
    sum(arrayfun(@(f) any(kcsRows.rank_changed(kcsRows.field_id == f)), kcsFields)), kcsN));
grid(kcsAx, 'on');

% Never overwrite: move previous outputs to old/<stamp>/.
kcsExisting = {kcsCsv, kcsPng};
kcsExisting = kcsExisting(cellfun(@isfile, kcsExisting));
if ~isempty(kcsExisting)
    kcsOld = fullfile(kcsOutDir, 'old', char(datetime('now', 'Format', 'yyyyMMdd_HHmmss')));
    mkdir(kcsOld);
    for kcsI = 1:numel(kcsExisting)
        movefile(kcsExisting{kcsI}, kcsOld);
    end
end
writetable(kcsRows, kcsCsv, 'Encoding', 'UTF-8');
exportgraphics(kcsFig, kcsPng, 'Resolution', 150);
fprintf('Wrote %s (%d rows) and %s\n', kcsCsv, height(kcsRows), kcsPng);

function [et0, prec, yearKey] = kcs_power_daily(powerFile)
    raw = jsondecode(fileread(powerFile));
    p = raw.properties.parameter;
    fNames = fieldnames(p.T2M);
    n = numel(fNames);
    tMean = zeros(n,1); tMax = zeros(n,1); tMin = zeros(n,1);
    prec = zeros(n,1); rad = zeros(n,1); dts = NaT(n,1);
    for i = 1:n
        fn = fNames{i};
        dts(i) = datetime(str2double(fn(2:5)), str2double(fn(6:7)), str2double(fn(8:9)));
        tMean(i) = p.T2M.(fn);
        tMax(i) = p.T2M_MAX.(fn);
        tMin(i) = p.T2M_MIN.(fn);
        prec(i) = p.PRECTOTCORR.(fn);
        rad(i) = p.ALLSKY_SFC_SW_DWN.(fn);
    end
    if any(~isfinite([tMean; tMax; tMin; prec; rad])) || any(tMean <= -90 | prec < 0 | rad < 0)
        error('KcSens:POWERInvalid', 'POWER daily series has missing/invalid values: %s', powerFile);
    end
    swSafe = max(5.0, rad);
    et0 = max(0, 0.0023 * (swSafe * 0.408) .* max(0, tMean + 17.8) .* sqrt(max(0, tMax - tMin)));
    inSeason = month(dts) >= 5 & month(dts) <= 9;
    dekad = min(3, ceil(day(dts) / 10));
    yearKey = nan(n, 1);
    yearKey(inSeason) = year(dts(inSeason)) * 100 + month(dts(inSeason)) * 10 + dekad(inSeason);
end

function d = kcs_season_deficit(kc, et0, peff, yearKey)
    m = ~isnan(yearKey);
    [g, keys] = findgroups(yearKey(m));
    dekDef = max(0, splitapply(@sum, kc * et0(m), g) - splitapply(@sum, peff(m), g));
    yrs = floor(keys / 100);
    d = mean(splitapply(@sum, dekDef, findgroups(yrs)));
end
