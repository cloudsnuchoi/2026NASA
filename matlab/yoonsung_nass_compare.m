function yoonsung_nass_compare()
% NASS 2012 county yield change vs engine 2012 deficit and drought indicator (4 counties, directional only).
% Base MATLAB only (no Statistics Toolbox). Press Run; no input needed.
% Yield change = 2012 yield vs mean of 2001-2011 + 2013-2024 (2025 excluded), as in docs/validation/NASS-2012.md.
% Engine deficit = strategy A season water deficit, mean of the project's demo fields per county.
% Drought indicator = precip_anomaly_pct_2012_MJJAS from drought_compare_2012_summary.csv (first round).
inputDir = '/data/processed/v1/matlab/inputs';
outputDir = '/data/processed/v1/matlab/outputs/yoonsung';
nassFile = '/data/processed/v1/validation/nass_yield.csv';
nass = read_csv(nassFile, ["county_fips","county","crop","year","yield_bu_ac"]);
fields = read_csv(fullfile(inputDir, 'fields_20.csv'), ["field_id","county_fips","county_label"]);
eng = read_csv(fullfile(inputDir, 'engine_2012_deficit.csv'), ...
    ["field_id","strategy_code","season_water_deficit_mm"]);
drought = read_csv(fullfile(outputDir, 'drought_compare_2012_summary.csv'), ...
    ["county_fips","county_label","precip_anomaly_pct_2012_MJJAS"]);

a = eng(eng.strategy_code == "A", :);
a = innerjoin(a, fields(:, {'field_id','county_fips'}), 'Keys', 'field_id');
counties = unique(fields.county_fips);
n = numel(counties);
labels = strings(n, 1); deficit = nan(n, 1); precipAnom = nan(n, 1);
corn = nan(n, 1); soy = nan(n, 1);
baseYears = [2001:2011, 2013:2024];
for k = 1:n
    c = counties(k);
    labels(k) = fields.county_label(find(fields.county_fips == c, 1));
    v = a.season_water_deficit_mm(a.county_fips == c);
    v = v(isfinite(v));
    if ~isempty(v), deficit(k) = mean(v); end
    d = drought.precip_anomaly_pct_2012_MJJAS(drought.county_fips == c);
    if ~isempty(d), precipAnom(k) = d(1); end
    corn(k) = yield_change(nass, c, "corn_grain", baseYears);
    soy(k) = yield_change(nass, c, "soybeans", baseYears);
end

pairs = {'corn_change_pct vs engine_A_deficit_mm', corn, deficit;
         'soy_change_pct vs engine_A_deficit_mm', soy, deficit;
         'corn_change_pct vs precip_anomaly_pct_2012_MJJAS', corn, precipAnom;
         'soy_change_pct vs precip_anomaly_pct_2012_MJJAS', soy, precipAnom};
np = size(pairs, 1);
pairName = strings(np, 1); nOk = zeros(np, 1); r = nan(np, 1); rho = nan(np, 1); note = strings(np, 1);
for p = 1:np
    y = pairs{p, 2}; x = pairs{p, 3};
    ok = isfinite(x) & isfinite(y);
    pairName(p) = pairs{p, 1}; nOk(p) = nnz(ok);
    if nOk(p) >= 3 && std(x(ok)) > 0 && std(y(ok)) > 0
        cc = corrcoef(x(ok), y(ok)); r(p) = cc(1, 2);
        cc = corrcoef(rank_avg(x(ok)), rank_avg(y(ok))); rho(p) = cc(1, 2);
    end
    note(p) = corr_note(r(p), nOk(p));
end
corrTable = table(pairName, nOk, r, rho, note, 'VariableNames', ...
    {'pair','n','pearson_r','spearman_rho','note'});

fig = figure('Visible', 'off', 'Color', 'w', 'Position', [100 100 1400 600]);
if isprop(fig, 'Theme'), fig.Theme = 'light'; end
cleanup = onCleanup(@() close(fig));
tl = tiledlayout(fig, 1, 2, 'TileSpacing', 'compact', 'Padding', 'compact');
title(tl, 'NASS 2012 county yield change vs engine and drought indicator (n = 4 counties, directional only)', ...
    'FontSize', 14, 'FontWeight', 'bold');
xs = {deficit, precipAnom};
xl = {'Engine 2012 water deficit, strategy A (mm)', 'MJJAS 2012 precipitation anomaly (%)'};
for t = 1:2
    ax = nexttile(tl); hold(ax, 'on'); grid(ax, 'on'); set(ax, 'Color', 'w', 'FontSize', 12);
    x = xs{t};
    h1 = scatter(ax, x, corn, 90, 'o', 'filled', 'MarkerFaceColor', [0.85 0.55 0.10]);
    h2 = scatter(ax, x, soy, 90, 's', 'filled', 'MarkerFaceColor', [0.20 0.45 0.70]);
    text(ax, x, corn, "  " + labels, 'FontSize', 11);
    text(ax, x, soy, "  " + labels, 'FontSize', 11, 'Color', [0.20 0.45 0.70]);
    yline(ax, 0, ':');
    xlabel(ax, xl{t}); ylabel(ax, 'NASS 2012 yield vs 2001-2024 baseline (%)');
    rc = r(2*t - 1); rs = r(2*t);
    title(ax, sprintf('corn r = %.2f, soy r = %.2f (n = %d)', rc, rs, nOk(2*t - 1)));
    legend(ax, [h1 h2], {'corn', 'soybeans'}, 'Location', 'best');
end
pngFile = fullfile(outputDir, 'nass_compare_2012.png');
csvFile = fullfile(outputDir, 'nass_compare_2012_corr.csv');
archive_existing_outputs(outputDir, {pngFile, csvFile});
writetable(corrTable, csvFile, 'Encoding', 'UTF-8');
exportgraphics(fig, pngFile, 'Resolution', 150, 'BackgroundColor', 'white');
for k = 1:n
    fprintf('%-10s deficit %6.1f mm  precip %6.1f %%  corn %6.1f %%  soy %6.1f %%\n', ...
        labels(k), deficit(k), precipAnom(k), corn(k), soy(k));
end
disp(corrTable);
fprintf('Saved %s and %s\n', pngFile, csvFile);
end

function pct = yield_change(nass, county, crop, baseYears)
rows = nass(nass.county_fips == county & nass.crop == crop, :);
y12 = rows.yield_bu_ac(rows.year == 2012);
base = rows.yield_bu_ac(ismember(rows.year, baseYears));
base = base(isfinite(base));
pct = NaN;
if numel(y12) == 1 && isfinite(y12) && ~isempty(base)
    pct = 100 * (y12 / mean(base) - 1);
end
end

function rk = rank_avg(v)
% Ranks with ties averaged (Spearman without Statistics Toolbox).
v = v(:); [~, order] = sort(v); rk = zeros(size(v));
rk(order) = 1:numel(v);
u = unique(v);
for k = 1:numel(u)
    m = v == u(k);
    rk(m) = mean(rk(m));
end
end

function s = corr_note(r, n)
if ~isfinite(r)
    s = "information gap: correlation not computable";
    return
end
if abs(r) < 0.5
    strength = "weak";
else
    strength = "moderate-to-strong in sign";
end
s = sprintf(['%s (r = %.2f) but unreliable: only n = %d counties, not statistically meaningful; ' ...
    'directional sanity check only, yield is not the engine objective'], strength, r, n);
s = string(s);
end

function t = read_csv(path, required)
assert(isfile(path), 'Information gap: missing input %s', path);
opts = detectImportOptions(path, 'Delimiter', ',', 'TextType', 'string');
idCols = intersect(opts.VariableNames, {'field_id','county_fips','county_label','county', ...
    'state','crop','strategy_code','source','retrieved_utc'});
opts = setvartype(opts, idCols, 'string');
num = intersect(opts.VariableNames, {'year','yield_bu_ac','season_water_deficit_mm', ...
    'precip_anomaly_pct_2012_MJJAS'});
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
