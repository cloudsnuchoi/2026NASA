function yoonsung_nass_compare_multi()
% NASS county yield change 2008-2023 vs engine seasonal water deficit (4 counties x 16 years, Pearson r and p per crop).
% Base MATLAB is enough (uses corr from Statistics Toolbox if present, else t-test p via betainc). Press Run; no input.
% Yield change = county yield vs that county's 2008-2023 mean (%). Engine deficit = API strategy A scored-year
% season water deficit, mean of the project's pilot fields in the county (engine_p90_years.csv, read-only).
% Validation only: yield is not the engine objective; p >= 0.05 is reported as "not statistically significant".
valDir = '/data/processed/v1/validation';
outputDir = '/data/processed/v1/matlab/outputs/yoonsung';
nass = read_csv(fullfile(valDir, 'nass_yield_multi.csv'), ...
    ["county_fips","county","crop","year","yield_bu_ac","yield_change_pct"]);
eng = read_csv(fullfile(valDir, 'engine_deficit_county_year.csv'), ...
    ["county_fips","year","engine_deficit_mm","n_fields"]);
j = innerjoin(nass(:, {'county_fips','county','crop','year','yield_change_pct'}), ...
    eng(:, {'county_fips','year','engine_deficit_mm'}), 'Keys', {'county_fips','year'});

crops = ["corn"; "soybean"];
nc = numel(crops);
crop = crops; n = zeros(nc, 1); r = nan(nc, 1); p = nan(nc, 1); note = strings(nc, 1);
for k = 1:nc
    s = j(j.crop == crops(k), :);
    ok = isfinite(s.yield_change_pct) & isfinite(s.engine_deficit_mm);
    n(k) = nnz(ok);
    [r(k), p(k)] = pearson_rp(s.engine_deficit_mm(ok), s.yield_change_pct(ok));
    note(k) = rp_note(r(k), p(k), n(k));
end
corrTable = table(crop, n, r, p, note);

fig = figure('Visible', 'off', 'Color', 'w', 'Position', [100 100 1400 600]);
if isprop(fig, 'Theme'), fig.Theme = 'light'; end
cleanup = onCleanup(@() close(fig));
tl = tiledlayout(fig, 1, nc, 'TileSpacing', 'compact', 'Padding', 'compact');
title(tl, 'NASS county yield change (2008-2023) vs engine season water deficit, 4 counties', ...
    'FontSize', 14, 'FontWeight', 'bold');
for k = 1:nc
    s = j(j.crop == crops(k), :);
    ax = nexttile(tl); hold(ax, 'on'); grid(ax, 'on'); set(ax, 'Color', 'w', 'FontSize', 12);
    h1 = scatter(ax, s.engine_deficit_mm, s.yield_change_pct, 50, 'o', 'filled', ...
        'MarkerFaceColor', [0.55 0.60 0.68]);
    m = s.year == 2012;
    h2 = scatter(ax, s.engine_deficit_mm(m), s.yield_change_pct(m), 120, 'd', 'filled', ...
        'MarkerFaceColor', [0.80 0.20 0.15]);
    text(ax, s.engine_deficit_mm(m), s.yield_change_pct(m), "  2012 " + s.county(m), ...
        'FontSize', 10, 'Color', [0.80 0.20 0.15]);
    yline(ax, 0, ':');
    xlabel(ax, 'Engine season water deficit, strategy A (mm)');
    ylabel(ax, 'NASS yield vs county 2008-2023 mean (%)');
    title(ax, sprintf('%s: r = %.2f, p = %.3g, n = %d', crops(k), r(k), p(k), n(k)));
    legend(ax, [h1 h2], {'county-year', '2012'}, 'Location', 'best');
end
pngFile = fullfile(outputDir, 'nass_compare_multi.png');
csvFile = fullfile(outputDir, 'nass_compare_multi_corr.csv');
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
    s = string(sprintf('not statistically significant (r = %.2f, p = %.3g, n = %d); directional check only', r, p, n));
else
    s = string(sprintf('statistically significant at p < 0.05 (r = %.2f, p = %.3g, n = %d); correlation only, not causation; 4 counties', r, p, n));
end
end

function t = read_csv(path, required)
assert(isfile(path), 'Information gap: missing input %s', path);
opts = detectImportOptions(path, 'Delimiter', ',', 'TextType', 'string');
idCols = intersect(opts.VariableNames, {'county_fips','county','state','crop','source'});
opts = setvartype(opts, idCols, 'string');
num = intersect(opts.VariableNames, {'year','yield_bu_ac','yield_change_pct', ...
    'county_mean_2008_2023','engine_deficit_mm','n_fields'});
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
