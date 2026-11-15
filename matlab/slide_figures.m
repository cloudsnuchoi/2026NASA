function slide_figures()
%SLIDE_FIGURES Offline slide PNGs; run slide_figures in MATLAB.
% Uses real exported engine outputs only; never synthesizes missing strategies
% or quantiles. Backtest is a MODEL hindcast, not observed yield validation.
% TODO(computation): choose the presentation's three fields with the team.
% Default is the first three sorted IDs COMMON to both snapshots, no ranking.
% TODO(computation): review engine_provenance.json alongside the figures before
% publication; document calibration assumptions and external validation gaps.

inputDir = '/data/processed/v1/matlab/inputs';
outputDir = '/data/processed/v1/matlab/outputs/jieun';
paths = {fullfile(outputDir, 'fig_p10p90.png'), ...
    fullfile(outputDir, 'fig_backtest2012.png')};
q = read_snapshot(fullfile(inputDir, 'engine_p10p90_20fields.csv'), ...
    ["field_id","strategy_code","metric","p10","p50","p90","unit"]);
b = read_snapshot(fullfile(inputDir, 'engine_2012_deficit.csv'), ...
    ["field_id","strategy_code","season_water_deficit_mm"]);
% This metric is explicitly present in the current exporter. Do not mix units
% or switch metrics silently when a snapshot is incomplete.
metric = "composite_index";
q = q(q.metric == metric, :);
assert(~isempty(q), 'Information gap: composite_index quantiles are missing.');
ids = intersect(unique(q.field_id), unique(b.field_id));
assert(numel(ids) >= 3, 'Information gap: need three fields in both snapshots.');
ids = ids(1:3);
strategies = ["A","B","C","D"];
assert(all(ismember(q.strategy_code, strategies)) && ...
    all(ismember(b.strategy_code, strategies)), 'Unexpected strategy_code.');
units = unique(q.unit(ismember(q.field_id, ids)));
assert(numel(units) == 1 && ~ismissing(units) && strlength(units) > 0, ...
    'Quantiles must have one explicit common unit.');
% Validate both figures completely before creating output files.
for fid = reshape(ids, 1, [])
    for strategy = strategies
        qr = q(q.field_id == fid & q.strategy_code == strategy, :);
        br = b(b.field_id == fid & b.strategy_code == strategy, :);
        assert(height(qr) == 1 && height(br) == 1, ...
            'Information gap or duplicate: field %s strategy %s.', fid, strategy);
        values = [qr.p10, qr.p50, qr.p90];
        assert(all(isfinite(values)) && qr.p10 <= qr.p50 && qr.p50 <= qr.p90, ...
            'Invalid/missing quantiles: field %s strategy %s.', fid, strategy);
        assert(isfinite(br.season_water_deficit_mm) && br.season_water_deficit_mm >= 0, ...
            'Invalid/missing backtest deficit: field %s strategy %s.', fid, strategy);
    end
end
archive_existing_outputs(outputDir, paths); % old outputs -> old/<stamp>/

fig = figure('Visible','off','Color','w','Position',[100 100 1500 560]);
cleanup = onCleanup(@() close(fig));
layout = tiledlayout(fig, 1, 3, 'TileSpacing','compact');
for k = 1:3
    ax = nexttile(layout);
    hold(ax, 'on');
    for s = 1:4
        r = q(q.field_id == ids(k) & q.strategy_code == strategies(s), :);
        errorbar(ax, s, r.p50, r.p50-r.p10, r.p90-r.p50, 'o', ...
            'LineWidth',1.8,'MarkerSize',7,'Color',[0.15 0.45 0.30]);
    end
    set(ax, 'XTick',1:4,'XTickLabel',cellstr(strategies),'XLim',[0.5 4.5]);
    xlabel(ax, 'Strategy (unranked)');
    ylabel(ax, sprintf('%s [%s]', metric, units), 'Interpreter','none');
    title(ax, "Field " + ids(k), 'Interpreter','none');
    grid(ax, 'on');
end
title(layout, {'ART FARM | Strategy scenarios: P10-P90, point = P50', ...
    'Screening estimates; uncertainty range is not a guarantee'});
save_new_png(fig, paths{1});
clear cleanup;

fig = figure('Visible','off','Color','w','Position',[100 100 1500 560]);
cleanup = onCleanup(@() close(fig));
layout = tiledlayout(fig, 1, 3, 'TileSpacing','compact');
for k = 1:3
    ax = nexttile(layout);
    values = nan(1,4);
    for s = 1:4
        r = b(b.field_id == ids(k) & b.strategy_code == strategies(s), :);
        values(s) = r.season_water_deficit_mm;
    end
    bar(ax, 1:4, values, 'FaceColor',[0.25 0.48 0.65]);
    set(ax, 'XTick',1:4,'XTickLabel',cellstr(strategies));
    xlabel(ax, 'Strategy (unranked)');
    ylabel(ax, 'Modelled seasonal water deficit [mm]');
    title(ax, "Field " + ids(k), 'Interpreter','none');
    grid(ax, 'on');
end
title(layout, {'ART FARM | 2012 drought: engine hindcast', ...
    'Screening estimates; not observed yield validation'});
save_new_png(fig, paths{2});
clear cleanup;
fprintf('Wrote %s\nWrote %s\n', paths{1}, paths{2});
end

function t = read_snapshot(path, required)
assert(isfile(path), 'Missing input snapshot (no fallback): %s', path);
opts = detectImportOptions(path, 'TextType','string');
assert(all(ismember(required, string(opts.VariableNames))), ...
    'Missing required columns in %s', path);
opts = setvartype(opts, {'field_id','strategy_code'}, 'string');
for name = ["metric","unit"]
    if ismember(name, string(opts.VariableNames))
        opts = setvartype(opts, char(name), 'string');
    end
end
for name = ["p10","p50","p90","season_water_deficit_mm"]
    if ismember(name, string(opts.VariableNames))
        opts = setvartype(opts, char(name), 'double');
    end
end
t = readtable(path, opts);
assert(~any(ismissing(t.field_id) | ismissing(t.strategy_code)), ...
    'Missing field/strategy ID in %s', path);
end

function save_new_png(fig, path)
% Previous deliverables were already moved to old/<stamp>/ by archive_existing_outputs.
exportgraphics(fig, path, 'Resolution',200);
end

function archive_existing_outputs(outputDir, files)
% Never overwrite: move previous outputs to <outputDir>/old/<yyyymmdd_HHMMSS>/.
if ~isfolder(outputDir), mkdir(outputDir); end
existing = files(cellfun(@isfile, files));
if isempty(existing), return; end
stamp = char(datetime('now', 'Format', 'yyyyMMdd_HHmmss'));
oldDir = fullfile(outputDir, 'old', stamp);
mkdir(oldDir);
for k = 1:numel(existing)
    movefile(existing{k}, oldDir);
end
fprintf('Previous outputs moved to %s\n', oldDir);
end
