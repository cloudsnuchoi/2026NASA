function yoonsung_season_anomaly()
% MJJAS POWER precipitation / FAO-56 reference ET0, 1995-2025.
inputDir = '/data/processed/v1/matlab/inputs';
outputDir = '/data/processed/v1/matlab/outputs/yoonsung';
t = read_snapshot(fullfile(inputDir, 'season_climate_1995_2025.csv'), ...
    ["county_fips","year","precip_mm","ET0_mm","precip_anomaly_mm","ET0_anomaly_mm"]);
p = read_snapshot(fullfile(inputDir, 'engine_p90_years.csv'), ...
    ["field_id","county_fips","year","is_p90","season","season_water_deficit_mm", ...
    "p90_threshold_mm","status","modelled_crop","window"]);
% Read scored engine years as numbers; climate and engine windows differ.
t.year = str2double(string(t.year));
p.year = str2double(string(p.year)); p.is_p90 = str2double(string(p.is_p90));
t = t(t.year >= 1995 & t.year <= 2025, :);
t = sortrows(t, {'county_fips','year'});
assert(height(unique(t(:, {'county_fips','year'}))) == height(t), 'Duplicate county/year');
assert(~isempty(t), 'Information gap: no seasonal history');
t.is_2012 = t.year == 2012;
t.is_p90 = nan(height(t), 1);
t.p90_status = repmat("information gap: no scored engine year (1995-1997 need spinup)", height(t), 1);
assert(height(unique(p(:, {'field_id','year'}))) == height(p), 'Duplicate engine field/year');
assert(all(p.season == "engine_scored_year"), 'Expected annual scored engine deficit');
for k = 1:height(t)
    rows = p.county_fips == t.county_fips(k) & p.year == t.year(k) & p.season == "engine_scored_year";
    flags = unique(p.is_p90(rows & isfinite(p.is_p90)));
    assert(all(ismember(flags, [0 1])), 'Invalid P90 flags');
    if ~isempty(flags)
        t.is_p90(k) = double(any(flags == 1));
        t.p90_status(k) = "union of per-field annual scored engine P90 years";
    end
end
counties = unique(t.county_fips);
fig = figure('Visible', 'off', 'Position', [100 100 1150 250*numel(counties)]);
cleanup = onCleanup(@() close(fig));
layout = tiledlayout(fig, numel(counties), 2, 'TileSpacing', 'compact');
for k = 1:numel(counties)
    c = t(t.county_fips == counties(k), :);
    for metric = ["precip_anomaly_mm","ET0_anomaly_mm"]
        values = c.(metric);
        nexttile; plot(c.year, values, '-o', 'MarkerSize', 3); hold on;
        yline(0, ':', 'HandleVisibility', 'off');
        d = c.is_2012 & isfinite(values);
        scatter(c.year(d), values(d), 65, 'r', 'filled', 'DisplayName', '2012');
        d = c.is_p90 == 1 & isfinite(values);
        scatter(c.year(d), values(d), 85, 'ks', 'DisplayName', 'Any field annual engine P90 year');
        xlim([1995 2025]); grid on; ylabel('Anomaly (mm)');
        title(counties(k) + " | " + metric, 'Interpreter', 'none');
        xlabel('Year (red: 2012; square: any field annual engine P90)');
    end
end
title(layout, {'MJJAS seasonal anomalies | baseline 1995-2011 + 2013-2024', ...
    '1988: outside export | P90: union of field annual scored deficits, not MJJAS | 1995-97 unavailable'});
pngFile = fullfile(outputDir, 'season_anomaly_1995_2025.png');
csvFile = fullfile(outputDir, 'season_anomaly_1995_2025.csv');
archive_existing_outputs(outputDir, {pngFile,csvFile});
writetable(t, csvFile, 'Encoding', 'UTF-8');
exportgraphics(fig, pngFile, 'Resolution', 200);
fprintf('Saved %s and %s; explicit P90 marks=%d\n', pngFile, csvFile, nnz(t.is_p90 == 1));
end

function t = read_snapshot(path, required)
assert(isfile(path), 'Information gap: missing input %s', path);
opts = detectImportOptions(path, 'Delimiter', ',', 'TextType', 'string');
idCols = intersect(opts.VariableNames, {'field_id','county_fips','county_label', ...
    'strategy_code','month','season','period','member','variable','unit','status','hazards'});
opts = setvartype(opts, idCols, 'string');
numericCols = intersect(opts.VariableNames, {'year','is_p90','value','baseline_value','anomaly', ...
    'precip_mm','ET0_mm','precip_anomaly_mm','ET0_anomaly_mm', ...
    'season_water_deficit_mm','rootmoist_kg_m2','mjjas_2012_rootmoist_kg_m2', ...
    'baseline_mjjas_rootmoist_kg_m2','anomaly_2012_kg_m2'});
opts = setvartype(opts, numericCols, 'double');
t = readtable(path, opts);
assert(all(ismember(required, string(t.Properties.VariableNames))), ...
    'Input schema mismatch: %s', path);
if ismember('county_fips', t.Properties.VariableNames)
    assert(all(~ismissing(t.county_fips) & strlength(t.county_fips) == 5), ...
        'county_fips must be five-character text in %s', path);
end
end

function archive_existing_outputs(outputDir, files)
if ~isfolder(outputDir), mkdir(outputDir); end
existing = files(cellfun(@isfile, files));
if isempty(existing), return; end
stamp = char(datetime('now', 'Format', 'yyyyMMdd_HHmmss_SSS'));
oldDir = fullfile(outputDir, 'old', stamp);
assert(~isfolder(oldDir), 'Archive already exists: %s', oldDir);
mkdir(oldDir);
for k = 1:numel(existing)
    movefile(existing{k}, oldDir);
end
fprintf('Previous outputs moved to %s\n', oldDir);
end
