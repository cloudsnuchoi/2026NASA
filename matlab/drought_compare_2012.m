function drought_compare_2012()
%DROUGHT_COMPARE_2012 Compare the engine's 2012 water deficit (model hindcast, per demo field)
% with Yoonsung's county 2012 drought anomalies (observations). Run: open this file -> Run.
% Different metrics: precipitation/soil-moisture anomaly (county) vs simulated season
% water deficit (field). We report them side by side and a Pearson r with its n; this is
% a consistency check, not a validation of yields. Missing values stay NaN (information gap).
inputDir  = '/data/processed/v1/matlab/inputs';
outputDir = '/data/processed/v1/matlab/outputs/yoonsung';
pngFile = fullfile(outputDir, 'drought_compare_2012.png');
csvFile = fullfile(outputDir, 'drought_compare_2012_summary.csv');
assert(~isfile(pngFile) && ~isfile(csvFile), 'Output exists already: rename or ask the bot before re-running.');

fields = read_ids_as_text(fullfile(inputDir, 'fields_20.csv'));
fields.field_id = string(fields.field_id); fields.county_fips = pad(string(fields.county_fips), 5, 'left', '0');
eng = read_ids_as_text(fullfile(inputDir, 'engine_2012_deficit.csv'));
eng.field_id = string(eng.field_id);
dro = read_ids_as_text(fullfile(inputDir, 'drought_2012_county.csv'));
dro.county_fips = pad(string(dro.county_fips), 5, 'left', '0');

engA = eng(eng.strategy_code == "A", :);
engA = innerjoin(engA, fields(:, {'field_id', 'county_fips', 'county_label'}), 'Keys', 'field_id');
counties = unique(engA.county_fips);
n = numel(counties);
deficit = nan(n, 1); nf = zeros(n, 1); label = strings(n, 1);
prcpPct = nan(n, 1); rzsmZ = nan(n, 1); tmaxAnom = nan(n, 1);
for k = 1:n
    m = engA.county_fips == counties(k);
    deficit(k) = mean(engA.season_water_deficit_mm(m), 'omitnan'); nf(k) = nnz(m);
    label(k) = engA.county_label(find(m, 1));
    d = dro(dro.county_fips == counties(k) & dro.period == "2012-MJJAS", :);
    v = d(d.variable == "precip_mm", :);  if ~isempty(v), prcpPct(k) = v.anomaly_pct(1); end
    v = d(d.variable == "rzsm", :);       if ~isempty(v), rzsmZ(k) = v.z_score(1); end
    v = d(d.variable == "tmax_c", :);     if ~isempty(v), tmaxAnom(k) = v.anomaly(1); end
end
ok = ~isnan(prcpPct) & ~isnan(deficit);
r = NaN; if nnz(ok) >= 3, c = corrcoef(prcpPct(ok), deficit(ok)); r = c(1, 2); end

summary = table(counties, label, nf, deficit, prcpPct, rzsmZ, tmaxAnom, ...
    'VariableNames', {'county_fips', 'county_label', 'n_fields', 'engine_A_deficit_2012_mm', ...
    'precip_anomaly_pct_2012_MJJAS', 'rzsm_z_2012_MJJAS', 'tmax_anomaly_c_2012_MJJAS'});
summary.pearson_r_precip_vs_deficit = repmat(r, n, 1);
summary.n_for_r = repmat(nnz(ok), n, 1);
writetable(summary, csvFile, 'Encoding', 'UTF-8');

fig = figure('Visible', 'off', 'Position', [100 100 900 420]);
tiledlayout(fig, 1, 2, 'TileSpacing', 'compact');
nexttile; bar(categorical(label), deficit); ylabel('Engine 2012 season water deficit, strategy A (mm)');
title('Model hindcast (field mean per county)');
nexttile; scatter(prcpPct, deficit, 60, 'filled'); text(prcpPct, deficit, "  " + label);
xlabel('2012 May–Sep precipitation anomaly (%)'); ylabel('Engine deficit (mm)');
title(sprintf('Pearson r = %.2f (n = %d counties)', r, nnz(ok))); grid on;
exportgraphics(fig, pngFile, 'Resolution', 200); close(fig);
fprintf('Saved %s and %s (r = %.2f, n = %d)\n', pngFile, csvFile, r, nnz(ok));
end

function t = read_ids_as_text(path)
% IDs (15-digit CSB field_id, 5-digit FIPS) must stay text, not double.
opts = detectImportOptions(path, 'Delimiter', ',', 'TextType', 'string');
idCols = intersect(opts.VariableNames, {'field_id', 'county_fips', 'variable', 'period', 'strategy_code', 'county_label'});
opts = setvartype(opts, idCols, 'string');
t = readtable(path, opts);
end
