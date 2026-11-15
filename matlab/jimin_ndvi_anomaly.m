function result = jimin_ndvi_anomaly()
% Run jimin_growing_season first. Available-year field mean, NOT climatology.
% Annual supported-day means receive equal weight across available years.
% Support varies by year; this is not a matched-season drought comparison.
outputDir = '/data/processed/v1/matlab/outputs/jimin';
if ~isfile(fullfile(outputDir, 'jimin_supported_daily.csv'))
    jimin_growing_season;
end
d = read_snapshot(fullfile(outputDir, 'jimin_supported_daily.csv'), ...
    ["field_id", "date", "year", "ndvi_smooth"]);
assert(~isempty(d) && all(d.year >= 2013), 'HLS cannot observe 2012');
keys = unique(d(:, {'field_id','year'}), 'rows');
result = keys;
result.ndvi_mean = nan(height(keys),1);
result.supported_days = zeros(height(keys),1);
for k = 1:height(keys)
    v = d.ndvi_smooth(d.field_id == keys.field_id(k) & d.year == keys.year(k));
    v = v(isfinite(v));
    result.supported_days(k) = numel(v);
    if ~isempty(v), result.ndvi_mean(k) = mean(v); end
end
result.field_available_year_mean = nan(height(keys),1);
result.baseline_year_count = zeros(height(keys),1);
result.baseline_years = strings(height(keys),1);
result.ndvi_anomaly = nan(height(keys),1);
result.status = repmat("information_gap_need_two_years",height(keys),1);
for k = 1:height(keys)
    same = result.field_id == keys.field_id(k) & isfinite(result.ndvi_mean);
    result.baseline_year_count(k) = sum(same);
    result.baseline_years(k) = strjoin(string(result.year(same)), ";");
    if any(same), result.field_available_year_mean(k) = mean(result.ndvi_mean(same)); end
    if sum(same) >= 2 && isfinite(result.ndvi_mean(k))
        result.ndvi_anomaly(k) = result.ndvi_mean(k)-result.field_available_year_mean(k);
        result.status(k) = "available_years_only_variable_support_not_climatology";
    end
end
path = fullfile(outputDir, 'jimin_ndvi_anomaly.csv');
png = fullfile(outputDir, 'ndvi_anomaly.png');
fig = figure('Visible', 'off', 'Position', [100 100 1200 700]);
cleanup = onCleanup(@() close(fig));
ids = unique(result.field_id);
hold on;
for f = 1:numel(ids)
    b = result(result.field_id == ids(f), :);
    plot(b.year, b.ndvi_anomaly, '-o', 'DisplayName', char(ids(f)));
end
yline(0, ':');
xlabel('Observed year (HLS; 2012 unavailable)');
ylabel('NDVI minus field available-year mean (unitless)');
title({'2012 not observable with HLS', ...
    'Variable supported-day coverage; not climatology or drought attribution'});
legend('Location', 'eastoutside', 'Interpreter', 'none');
grid on;
archive_existing_outputs(outputDir, {path, png});
writetable(result, path, 'Encoding', 'UTF-8');
exportgraphics(fig, png, 'Resolution', 150);
fprintf('Saved %s; 2012 not observable with HLS.\n', path);
end

function t = read_snapshot(path, required)
assert(isfile(path), 'Missing input (no fallback): %s', path);
opts = detectImportOptions(path, 'TextType', 'string');
assert(all(ismember(required, string(opts.VariableNames))), 'Missing columns: %s', path);
opts = setvartype(opts, 'field_id', 'string');
for name = ["date", "item", "value", "unit", "source", "run_id"]
    if ismember(name, string(opts.VariableNames))
        opts = setvartype(opts, char(name), 'string');
    end
end
numericCols = intersect(opts.VariableNames, {'ndvi','valid_frac','year','ndvi_smooth'});
if ~isempty(numericCols)
    opts = setvartype(opts, numericCols, 'double');
end
t = readtable(path, opts);
assert(~any(ismissing(t.field_id) | strlength(t.field_id) == 0), 'Missing field_id');
end

function archive_existing_outputs(outputDir, files)
if ~isfolder(outputDir), mkdir(outputDir); end
existing = files(cellfun(@isfile, files));
if isempty(existing), return; end
stamp = char(datetime('now', 'Format', 'yyyyMMdd_HHmmss_SSS'));
oldDir = fullfile(outputDir, 'old', stamp);
assert(~isfolder(oldDir), 'Archive already exists; retry Run.');
mkdir(oldDir);
for k = 1:numel(existing)
    movefile(existing{k}, oldDir);
end
end
