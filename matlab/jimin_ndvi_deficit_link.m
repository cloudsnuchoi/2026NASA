function jimin_ndvi_deficit_link()
% Field-year HLS NDVI anomaly and season length (2023-2025) vs engine season water deficit, 20 fields (Pearson r, p, n).
% Base MATLAB is enough (uses corr from Statistics Toolbox if present, else t-test p via betainc). Press Run; no input.
% Inputs: your growing_season_20fields.csv and jimin_ndvi_anomaly.csv (earlier rounds) and engine_p90_years.csv
% (API strategy A scored-year deficit per field-year, read-only). NDVI baseline is only the available years
% (2023-2025), so this is a screening check, not a climatology. p >= 0.05 is "not statistically significant".
inputDir = '/data/processed/v1/matlab/inputs';
outputDir = '/data/processed/v1/matlab/outputs/jimin';
gs = read_csv(fullfile(outputDir, 'growing_season_20fields.csv'), ["field_id","year","season_length_days"]);
an = read_csv(fullfile(outputDir, 'jimin_ndvi_anomaly.csv'), ["field_id","year","ndvi_anomaly"]);
eng = read_csv(fullfile(inputDir, 'engine_p90_years.csv'), ["field_id","year","season_water_deficit_mm"]);

j = innerjoin(an(:, {'field_id','year','ndvi_anomaly'}), ...
    eng(:, {'field_id','year','season_water_deficit_mm'}), 'Keys', {'field_id','year'});
j = innerjoin(j, gs(:, {'field_id','year','season_length_days'}), 'Keys', {'field_id','year'});

pairs = ["ndvi_anomaly vs season_water_deficit_mm"; "season_length_days vs season_water_deficit_mm"];
ys = {j.ndvi_anomaly, j.season_length_days};
x = j.season_water_deficit_mm;
np = numel(pairs);
pair = pairs; n = zeros(np, 1); r = nan(np, 1); p = nan(np, 1); note = strings(np, 1);
for k = 1:np
    y = ys{k};
    ok = isfinite(x) & isfinite(y);
    n(k) = nnz(ok);
    [r(k), p(k)] = pearson_rp(x(ok), y(ok));
    note(k) = rp_note(r(k), p(k), n(k));
end
corrTable = table(pair, n, r, p, note);

fig = figure('Visible', 'off', 'Color', 'w', 'Position', [100 100 1400 600]);
if isprop(fig, 'Theme'), fig.Theme = 'light'; end
cleanup = onCleanup(@() close(fig));
tl = tiledlayout(fig, 1, np, 'TileSpacing', 'compact', 'Padding', 'compact');
title(tl, 'HLS NDVI (2023-2025, 20 fields) vs engine season water deficit - screening only', ...
    'FontSize', 14, 'FontWeight', 'bold');
yl = {'NDVI anomaly vs field mean of available years', 'Growing season length (days)'};
yrs = [2023 2024 2025]; colors = [0.20 0.45 0.70; 0.85 0.55 0.10; 0.30 0.65 0.35];
for k = 1:np
    ax = nexttile(tl); hold(ax, 'on'); grid(ax, 'on'); set(ax, 'Color', 'w', 'FontSize', 12);
    h = gobjects(numel(yrs), 1);
    for q = 1:numel(yrs)
        m = j.year == yrs(q);
        h(q) = scatter(ax, x(m), ys{k}(m), 60, 'o', 'filled', 'MarkerFaceColor', colors(q, :));
    end
    xlabel(ax, 'Engine season water deficit, strategy A (mm)'); ylabel(ax, yl{k});
    title(ax, sprintf('r = %.2f, p = %.3g, n = %d', r(k), p(k), n(k)));
    legend(ax, h, cellstr(string(yrs)), 'Location', 'best');
end
pngFile = fullfile(outputDir, 'ndvi_vs_deficit.png');
csvFile = fullfile(outputDir, 'ndvi_vs_deficit.csv');
archive_existing_outputs(outputDir, {pngFile, csvFile});
writetable(corrTable, csvFile, 'Encoding', 'UTF-8');
exportgraphics(fig, pngFile, 'Resolution', 150, 'BackgroundColor', 'white');
disp(corrTable);
fprintf('Saved %s and %s\n', pngFile, csvFile);
end

function [r, p] = pearson_rp(x, y)
% Pearson r with two-sided p (t-test, df = n-2).
x = x(:); y = y(:); r = NaN; p = NaN; nn = numel(x);
if nn < 3 || std(x) == 0 || std(y) == 0, return; end
if license('test', 'Statistics_Toolbox') && exist('corr', 'file') == 2
    [r, p] = corr(x, y, 'Type', 'Pearson');
    return
end
cc = corrcoef(x, y); r = cc(1, 2);
df = nn - 2;
if abs(r) >= 1, p = 0; return; end
t = r * sqrt(df / (1 - r^2));
p = betainc(df / (df + t^2), df / 2, 0.5);
end

function s = rp_note(r, p, n)
if ~isfinite(r) || ~isfinite(p)
    s = "information gap: correlation not computable";
elseif p >= 0.05
    s = string(sprintf('not statistically significant (r = %.2f, p = %.3g, n = %d); screening only', r, p, n));
else
    s = string(sprintf('statistically significant at p < 0.05 (r = %.2f, p = %.3g, n = %d); correlation only, 3 years of NDVI', r, p, n));
end
end

function t = read_csv(path, required)
assert(isfile(path), 'Information gap: missing input %s', path);
opts = detectImportOptions(path, 'Delimiter', ',', 'TextType', 'string');
idCols = intersect(opts.VariableNames, {'field_id','county_fips','status','season','modelled_crop', ...
    'window','baseline_years'});
opts = setvartype(opts, idCols, 'string');
num = intersect(opts.VariableNames, {'year','ndvi_anomaly','season_length_days','season_water_deficit_mm'});
opts = setvartype(opts, num, 'double');
t = readtable(path, opts);
assert(all(ismember(required, string(t.Properties.VariableNames))), ...
    'Input schema mismatch: %s', path);
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
