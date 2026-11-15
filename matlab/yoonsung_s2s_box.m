function yoonsung_s2s_box()
% Base MATLAB distribution boxes; no Statistics Toolbox or online requests.
% JJ is June-July only. Historical POWER is not a bias-correcting hindcast.
inputDir = '/data/processed/v1/matlab/inputs';
outputDir = '/data/processed/v1/matlab/outputs/yoonsung';
g = read_snapshot(fullfile(inputDir, 'geos_s2s_next_season.csv'), ...
    ["county_fips","season","period","member","variable","value","baseline_value","anomaly","unit"]);
h = read_snapshot(fullfile(inputDir, 'historical_31yr_distribution.csv'), ...
    ["county_fips","season","period","year","variable","value","baseline_value","anomaly","unit"]);
h.year = str2double(string(h.year));
h = h(h.year >= 1995 & h.year <= 2025, :);
assert(all(ismember(g.season, ["MAM","JJ"])) && all(ismember(h.season, ["MAM","JJ"])), ...
    'Expected MAM or JJ (June-July, not JJA)');
assert(all(ismember(g.variable, ["pr","tas"])) && all(ismember(h.variable, ["pr","tas"])), ...
    'Expected pr or tas');
assert(height(unique(g(:, {'county_fips','season','period','member','variable'}))) == height(g), ...
    'Duplicate GEOS member');
assert(height(unique(h(:, {'county_fips','season','year','variable'}))) == height(h), ...
    'Duplicate historical year');
assert(~isempty(g) && ~isempty(h), 'Information gap: empty seasonal distribution');
counties = unique(g.county_fips); seasons = ["MAM","JJ"];
summary = table();
files = {fullfile(outputDir, 's2s_vs_history_box.png'), ...
    fullfile(outputDir, 's2s_vs_history_box.csv')};
% Validate all groups and build figures before archiving any previous results.
fig = figure('Visible', 'off', 'Position', [100 100 1600 280*numel(counties)]);
cleanup = onCleanup(@() close(fig));
layout = tiledlayout(fig, numel(counties), 4, 'TileSpacing', 'compact');
variables = ["pr","tas"]; units = ["mm/day","degC"];
for vi = 1:2
    variable = variables(vi); unit = units(vi);
    for ci = 1:numel(counties)
        for si = 1:2
            season = seasons(si);
            a = g(g.county_fips == counties(ci) & g.season == season & g.variable == variable, :);
            b = h(h.county_fips == counties(ci) & h.season == season & h.variable == variable, :);
            assert(all(a.unit == unit) && all(b.unit == unit), 'Seasonal unit mismatch');
            assert(numel(unique(a.period)) <= 1, 'Multiple forecast periods in one group');
            assert(all(~ismissing(a.member)), 'Missing GEOS member ID');
            assert(height(a) <= 10, 'Expected exported subset of at most 10 GEOS members');
            forecast = a.anomaly(isfinite(a.anomaly)); history = b.anomaly(isfinite(b.anomaly));
            qg = empirical_quantiles(forecast, [0.1 0.25 0.5 0.75 0.9]);
            qh = empirical_quantiles(history, [0.1 0.25 0.5 0.75 0.9]);
            status = "complete: 10 members and 31 historical years";
            if numel(forecast) ~= 10 || numel(history) ~= 31
                status = "information gap: incomplete member or historical distribution";
            end
            period = "information gap";
            if ~isempty(a), period = a.period(1); end
            row = table(counties(ci), season, period, variable, unit, numel(forecast), numel(history), ...
                qg(1), qg(3), qg(5), qh(1), qh(3), qh(5), status, 'VariableNames', ...
                {'county_fips','season','period','variable','unit','n_members','n_history_years', ...
                'geos_p10','geos_p50','geos_p90','history_p10','history_p50','history_p90','status'});
            summary = [summary; row]; %#ok<AGROW>
            ax = nexttile(layout, (ci-1)*4 + (vi-1)*2 + si); hold(ax, 'on');
            draw_distribution(ax, history, qh, 1, [0.2 0.5 0.8]);
            draw_distribution(ax, forecast, qg, 2, [0.9 0.5 0.2]);
            xticks(ax, [1 2]); xticklabels(ax, {'POWER 1995-2025','GEOS 2027'});
            xlim(ax, [0.5 2.5]); ylabel(ax, variable + " anomaly (" + unit + ")"); grid(ax, 'on');
            title(ax, sprintf('%s | %s | n=%d / %d', counties(ci), season, numel(history), numel(forecast)));
        end
    end
end
title(layout, {'Possible ranges (scenarios): MAM = Mar-May; JJ = Jun-Jul (no August)', ...
        'Box P25-P75, median; whiskers P10-P90; dots all samples | POWER baseline anomalies, no GEOS hindcast bias correction'});
archive_existing_outputs(outputDir, files);
summary.distribution_basis = repmat("anomaly relative to exported POWER baseline", height(summary), 1);
writetable(summary, files{2}, 'Encoding', 'UTF-8');
exportgraphics(fig, files{1}, 'Resolution', 200);
fprintf('Saved %s and %s\n', files{:});
end

function q = empirical_quantiles(values, probabilities)
% Linear interpolation at 1+(n-1)*p; no toolbox percentile dependency.
v = sort(values(:)); q = nan(size(probabilities));
if isempty(v), return; end
for k = 1:numel(probabilities)
    index = 1 + (numel(v)-1)*probabilities(k);
    lo = floor(index); hi = ceil(index);
    q(k) = v(lo) + (index-lo)*(v(hi)-v(lo));
end
end

function draw_distribution(ax, values, q, x, color)
if isempty(values)
    text(ax, x, 0, 'information gap', 'HorizontalAlignment', 'center');
    return;
end
% Whiskers explicitly P10-P90, not Tukey whiskers or confidence intervals.
line(ax, [x x], q([1 5]), 'Color', color, 'LineWidth', 1.5);
patch(ax, x+[-0.2 0.2 0.2 -0.2], q([2 2 4 4]), color, 'FaceAlpha', 0.25);
line(ax, x+[-0.2 0.2], [q(3) q(3)], 'Color', color, 'LineWidth', 2);
scatter(ax, x+linspace(-0.12, 0.12, numel(values)), sort(values), 15, color, 'filled');
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
