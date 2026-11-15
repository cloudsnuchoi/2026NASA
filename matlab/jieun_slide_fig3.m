function jieun_slide_fig3()
% Slide figure 3 (16:9, 1920x1080): Yoonsung's three extra results re-plotted from their CSVs on one slide.
% Base MATLAB only. Press Run; no input needed. White background, large fonts.
% Panels: (a) NLDAS 2012 root-moisture anomaly vs engine deficit, (b) MJJAS precipitation anomaly 1995-2025,
% (c) GEOS-S2S 2027 range vs 31-year history (P10-P90, distributions only, not a forecast value).
srcDir = '/data/processed/v1/matlab/outputs/yoonsung';
outDir = '/data/processed/v1/matlab/outputs/jieun';
nl = read_csv(fullfile(srcDir, 'nldas_vs_engine_2012.csv'), ["county_fips","county_label", ...
    "engine_A_deficit_2012_mm","anomaly_2012_kg_m2","pearson_r","n_counties_for_r"]);
sa = read_csv(fullfile(srcDir, 'season_anomaly_1995_2025.csv'), ["county_fips","year","precip_anomaly_mm"]);
sb = read_csv(fullfile(srcDir, 's2s_vs_history_box.csv'), ["county_fips","season","variable","unit", ...
    "geos_p10","geos_p50","geos_p90","history_p10","history_p50","history_p90"]);
names = containers.Map(cellstr(nl.county_fips), cellstr(nl.county_label));

fig = figure('Visible', 'off', 'Color', 'w', 'Units', 'pixels', 'Position', [0 0 1920 1080]);
if isprop(fig, 'Theme'), fig.Theme = 'light'; end
cleanup = onCleanup(@() close(fig));
tl = tiledlayout(fig, 1, 3, 'TileSpacing', 'loose', 'Padding', 'loose');
title(tl, 'Climate context for the 4 study counties (Yoonsung, MATLAB)', 'FontSize', 26, 'FontWeight', 'bold');
subtitle(tl, 'County-level context, not field validation · future = range (scenario), not a forecast', 'FontSize', 16);

% (a) NLDAS vs engine
ax = nexttile(tl); style(ax);
ok = isfinite(nl.anomaly_2012_kg_m2) & isfinite(nl.engine_A_deficit_2012_mm);
scatter(ax, nl.anomaly_2012_kg_m2(ok), nl.engine_A_deficit_2012_mm(ok), 160, 'filled', ...
    'MarkerFaceColor', [0.80 0.35 0.15]);
text(ax, nl.anomaly_2012_kg_m2(ok), nl.engine_A_deficit_2012_mm(ok), "  " + nl.county_label(ok), 'FontSize', 15);
xlabel(ax, 'NLDAS MJJAS 2012 root moisture anomaly (kg/m^2)');
ylabel(ax, 'Engine 2012 deficit, strategy A (mm)');
title(ax, sprintf('(a) 2012: r = %.2f, n = %d counties', nl.pearson_r(1), nl.n_counties_for_r(1)), 'FontSize', 20);

% (b) season precipitation anomaly
ax = nexttile(tl); style(ax);
cs = unique(sa.county_fips);
for k = 1:numel(cs)
    m = sa.county_fips == cs(k);
    plot(ax, sa.year(m), sa.precip_anomaly_mm(m), '-o', 'LineWidth', 2, 'MarkerSize', 4, ...
        'DisplayName', label_of(names, cs(k)));
end
xline(ax, 2012, '--', '2012', 'LineWidth', 2, 'FontSize', 15, 'HandleVisibility', 'off');
yline(ax, 0, ':', 'HandleVisibility', 'off');
legend(ax, 'Location', 'southoutside', 'NumColumns', 2, 'FontSize', 14);
xlabel(ax, 'Year'); ylabel(ax, 'MJJAS precipitation anomaly (mm)');
title(ax, '(b) Growing-season rain, 1995-2025', 'FontSize', 20);

% (c) S2S vs history, precipitation, JJ
ax = nexttile(tl); style(ax);
p = sb(sb.variable == "pr" & sb.season == "JJ", :);
x = 1:height(p);
errorbar(ax, x - 0.12, p.history_p50, p.history_p50 - p.history_p10, p.history_p90 - p.history_p50, ...
    'o', 'LineWidth', 3, 'MarkerSize', 10, 'Color', [0.45 0.45 0.45], 'DisplayName', 'History 1995-2025');
errorbar(ax, x + 0.12, p.geos_p50, p.geos_p50 - p.geos_p10, p.geos_p90 - p.geos_p50, ...
    's', 'LineWidth', 3, 'MarkerSize', 10, 'Color', [0.15 0.40 0.75], 'DisplayName', 'GEOS-S2S 2027');
yline(ax, 0, ':', 'HandleVisibility', 'off');
xticks(ax, x); xticklabels(ax, cellfun(@(c) label_of(names, string(c)), cellstr(p.county_fips), 'UniformOutput', false));
xlim(ax, [0.5, max(x) + 0.5]);
ylabel(ax, sprintf('Jun-Jul precipitation anomaly (%s), P10-P50-P90', p.unit(1)));
legend(ax, 'Location', 'southoutside', 'FontSize', 14);
title(ax, '(c) Possible range (scenario), Jun-Jul 2027', 'FontSize', 20);

pngFile = fullfile(outDir, 'fig3_yoonsung_extra.png');
archive_existing_outputs(outDir, {pngFile});
set(fig, 'PaperUnits', 'inches', 'PaperPosition', [0 0 19.2 10.8], 'PaperSize', [19.2 10.8], ...
    'InvertHardcopy', 'off');
print(fig, pngFile, '-dpng', '-r100');
info = imfinfo(pngFile);
fprintf('Saved %s (%dx%d)\n', pngFile, info.Width, info.Height);
end

function style(ax)
hold(ax, 'on'); grid(ax, 'on');
set(ax, 'Color', 'w', 'FontSize', 15, 'XColor', 'k', 'YColor', 'k', 'LineWidth', 1.2);
end

function s = label_of(names, fips)
s = char(fips);
if isKey(names, s), s = names(s); end
end

function t = read_csv(path, required)
assert(isfile(path), 'Information gap: missing input %s (run Yoonsung''s extra scripts first)', path);
opts = detectImportOptions(path, 'Delimiter', ',', 'TextType', 'string');
idCols = intersect(opts.VariableNames, {'county_fips','county_label','season','period','variable', ...
    'unit','status','distribution_basis','p90_status'});
opts = setvartype(opts, idCols, 'string');
t = readtable(path, opts);
assert(all(ismember(required, string(t.Properties.VariableNames))), 'Input schema mismatch: %s', path);
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
