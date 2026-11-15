function result = ndvi_baresoil()
%NDVI_BARESOIL Offline, provisional low-NDVI screening; run ndvi_baresoil.
% Inputs are the exported 20-field snapshots, not a live DB/API request.
% bare_days is a PARTIAL-YEAR count on supported days, not an annual total.
% observed_days means observationally supported days AFTER bounded linear
% interpolation and SG smoothing (not the number of satellite acquisitions).
% coverage = observed_days / 365; Feb 29 is excluded to match the engine.
% No extrapolation, zero filling, cross-year smoothing, or annual scaling.
% TODO(computation): calibrate threshold, QA, gap limit and SG window against
% local ground truth. NDVI < 0.3 is PROVISIONAL, NOT a universal established
% bare-soil threshold: snow, residue, water and cloud can also lower NDVI.
% TODO(computation): assess sensitivity and distinguish residue from bare soil
% before interpreting these screening counts as erosion exposure.

inputDir = '/data/processed/v1/matlab/inputs';
outputDir = '/data/processed/v1/matlab/outputs/jimin';
outputFile = fullfile(outputDir, 'baresoil_days_20fields.csv');
threshold = 0.3;           % Provisional team screening parameter, not evidence.
validFracMin = 0.5;        % Provisional QA setting from matlab/TASKS.md.
maxGapDays = 20;           % Provisional interpolation cap; do not bridge winter.
sgWindow = 11;            % Provisional daily SG window, quadratic polynomial.

obs = read_snapshot(fullfile(inputDir, 'ndvi_hls_20fields.csv'), ...
    ["field_id", "date", "ndvi", "valid_frac"]);
fields = read_snapshot(fullfile(inputDir, 'fields_20.csv'), "field_id");
assert(height(fields) == 20 && numel(unique(fields.field_id)) == 20, ...
    'Expected 20 distinct fields in fields_20.csv.');
assert(all(ismember(obs.field_id, fields.field_id)), 'Unknown NDVI field_id.');
obs.date = datetime(obs.date, 'InputFormat', 'yyyy-MM-dd');
assert(~any(isnat(obs.date)), 'Invalid NDVI dates.');
% Retain all input years, even if every observation fails QA in a field-year.
years = unique(year(obs.date));
assert(~isempty(years), 'NDVI input has no dated observations.');
result = table('Size', [height(fields)*numel(years), 6], ...
    'VariableTypes', {'string','double','double','double','double','double'}, ...
    'VariableNames', {'field_id','year','bare_days','winter_bare_days', ...
    'observed_days','coverage'});
row = 0;
for f = 1:height(fields)
    for y = reshape(years, 1, [])
        row = row + 1;
        dates = (datetime(y,1,1):caldays(1):datetime(y,12,31))';
        raw = nan(numel(dates), 1);
        select = obs.field_id == fields.field_id(f) & year(obs.date) == y;
        block = obs(select, :);
        valid = isfinite(block.ndvi) & block.ndvi >= -1 & block.ndvi <= 1 ...
            & isfinite(block.valid_frac) & block.valid_frac >= validFracMin ...
            & block.valid_frac <= 1;
        block = block(valid, :);
        % Collapse multiple sensors on the same day; never count a day twice.
        [daysSeen, ~, group] = unique(block.date);
        if ~isempty(daysSeen)
            means = accumarray(group, block.ndvi, [], @mean);
            [~, pos] = ismember(daysSeen, dates);
            raw(pos) = means;
        end
        filled = raw;
        known = find(isfinite(raw));
        for k = 1:numel(known)-1
            a = known(k); b = known(k+1);
            if b-a <= maxGapDays
                filled(a:b) = interp1([a;b], raw([a;b]), (a:b)', 'linear');
            end
        end
        % SG on each contiguous supported segment only. Short segments remain
        % unknown; fitting across a cloud gap would invent unsupported days.
        smoothed = nan(size(raw));
        edges = diff([false; isfinite(filled); false]);
        starts = find(edges == 1); stops = find(edges == -1)-1;
        for k = 1:numel(starts)
            idx = starts(k):stops(k);
            if numel(idx) >= sgWindow
                smoothed(idx) = smoothdata(filled(idx), 'sgolay', sgWindow, 'Degree', 2);
            end
        end
        % model_api/hydro.py WINTER_MASK: Jan-Apr + Nov-Dec of SAME year,
        % not DJF and not Nov(previous year)-Apr. Engine omits leap days.
        scored = ~(month(dates) == 2 & day(dates) == 29);
        supported = isfinite(smoothed) & scored;
        winter = month(dates) <= 4 | month(dates) >= 11;
        bare = supported & smoothed < threshold;
        bareDays = NaN; winterBareDays = NaN;
        if any(supported)
            bareDays = sum(bare);
        end
        if any(supported & winter)
            winterBareDays = sum(bare & winter);
        end
        nSupported = sum(supported);
        result(row,:) = {fields.field_id(f), y, bareDays, winterBareDays, ...
            nSupported, nSupported/sum(scored)};
    end
end
% Numeric NaN cells are written as empty CSV fields by writetable.
archive_existing_outputs(outputDir, {outputFile}); % old outputs -> old/<stamp>/
writetable(result, outputFile, 'Encoding', 'UTF-8');
fprintf('Wrote %s (%d field-years); provisional screening counts only.\n', ...
    outputFile, height(result));
end

function t = read_snapshot(path, required)
assert(isfile(path), 'Missing input snapshot (no fallback): %s', path);
opts = detectImportOptions(path, 'TextType', 'string');
assert(all(ismember(required, string(opts.VariableNames))), ...
    'Missing required columns in %s', path);
opts = setvartype(opts, 'field_id', 'string'); % Preserve CSB IDs exactly.
if ismember('date', opts.VariableNames)
    opts = setvartype(opts, 'date', 'string');
end
for name = ["ndvi", "valid_frac"]
    if ismember(name, string(opts.VariableNames))
        opts = setvartype(opts, char(name), 'double');
    end
end
t = readtable(path, opts);
assert(~any(ismissing(t.field_id) | strlength(t.field_id) == 0), ...
    'Missing field_id in %s', path);
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
