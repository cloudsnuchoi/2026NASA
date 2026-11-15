function yoonsung_nldas_2012()
% Run in the Editor. Base MATLAB only; county context, not field validation.
inputDir = '/data/processed/v1/matlab/inputs';
outputDir = '/data/processed/v1/matlab/outputs/yoonsung';
fields = read_snapshot(fullfile(inputDir, 'fields_20.csv'), ...
    ["field_id","county_fips","county_label"]);
eng = read_snapshot(fullfile(inputDir, 'engine_2012_deficit.csv'), ...
    ["field_id","strategy_code","season_water_deficit_mm"]);
nldas = read_snapshot(fullfile(inputDir, 'county_nldas_2012.csv'), ...
    ["county_fips","month","rootmoist_kg_m2","mjjas_2012_rootmoist_kg_m2", ...
    "baseline_mjjas_rootmoist_kg_m2","anomaly_2012_kg_m2"]);
assert(numel(unique(fields.field_id)) == height(fields), 'Duplicate field mapping');
a = eng(eng.strategy_code == "A", :);
assert(numel(unique(a.field_id)) == height(a), 'Duplicate strategy A field');
assert(all(ismember(a.field_id, fields.field_id)), 'Unmapped engine field');
a = innerjoin(a, fields(:, {'field_id','county_fips','county_label'}), 'Keys', 'field_id');
counties = unique(fields.county_fips);
n = numel(counties);
labels = strings(n, 1); deficit = nan(n, 1); nFields = zeros(n, 1);
root2012 = nan(n, 1); baseline = nan(n, 1); anomaly = nan(n, 1);
for k = 1:n
    labels(k) = fields.county_label(find(fields.county_fips == counties(k), 1));
    v = a.season_water_deficit_mm(a.county_fips == counties(k));
    v = v(isfinite(v)); nFields(k) = numel(v);
    if ~isempty(v), deficit(k) = mean(v); end
    % Summary is repeated monthly: use each county once, never correlate months.
    c = nldas(nldas.county_fips == counties(k), :);
    root2012(k) = county_summary(c.mjjas_2012_rootmoist_kg_m2);
    baseline(k) = county_summary(c.baseline_mjjas_rootmoist_kg_m2);
    anomaly(k) = county_summary(c.anomaly_2012_kg_m2);
end
ok = isfinite(deficit) & isfinite(anomaly);
r = NaN;
if nnz(ok) >= 3 && std(deficit(ok)) > 0 && std(anomaly(ok)) > 0
    c = corrcoef(anomaly(ok), deficit(ok)); r = c(1, 2);
end
summary = table(counties, labels, nFields, deficit, root2012, baseline, anomaly, ...
    repmat(r, n, 1), repmat(nnz(ok), n, 1), 'VariableNames', ...
    {'county_fips','county_label','n_finite_fields','engine_A_deficit_2012_mm', ...
    'mjjas_2012_rootmoist_kg_m2','baseline_mjjas_rootmoist_kg_m2', ...
    'anomaly_2012_kg_m2','pearson_r','n_counties_for_r'});
pngFile = fullfile(outputDir, 'nldas_vs_engine_2012.png');
csvFile = fullfile(outputDir, 'nldas_vs_engine_2012.csv');
fig = figure('Visible', 'off', 'Position', [100 100 1050 450]);
cleanup = onCleanup(@() close(fig));
tiledlayout(fig, 1, 2);
nexttile; bar(categorical(labels), deficit); ylabel('Strategy A deficit (mm)');
title('2012 engine hindcast: mean of demo fields');
nexttile; scatter(anomaly(ok), deficit(ok), 65, 'filled');
text(anomaly(ok), deficit(ok), "  " + labels(ok)); grid on;
xlabel('NLDAS MJJAS root moisture anomaly (kg/m^2)'); ylabel('Engine deficit (mm)');
title(sprintf('County consistency only: r=%.3f, n=%d', r, nnz(ok)));
archive_existing_outputs(outputDir, {pngFile,csvFile});
writetable(summary, csvFile, 'Encoding', 'UTF-8');
exportgraphics(fig, pngFile, 'Resolution', 200);
fprintf('Saved %s and %s (r=%.4f, n=%d counties)\n', pngFile, csvFile, r, nnz(ok));
end

function value = county_summary(values)
values = unique(values(isfinite(values)));
assert(numel(values) <= 1, 'Inconsistent repeated county NLDAS summary');
value = NaN;
if ~isempty(values), value = values(1); end
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
