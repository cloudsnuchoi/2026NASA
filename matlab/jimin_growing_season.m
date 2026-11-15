function season = jimin_growing_season()
% Offline HLS screening, no toolbox or interaction required.
% QA >=0.5, max interpolation gap 20 days, 11-day quadratic SG are
% PROVISIONAL team parameters (same as ndvi_baresoil), not calibrated truth.
% Transition threshold = min + 0.2*(max-min), provisional amplitude fraction.
% Only adjacent supported-day crossings around the annual maximum count.
% Multiple seasons, cloud gaps and missing transitions remain information gaps.
inputDir = '/data/processed/v1/matlab/inputs';
outputDir = '/data/processed/v1/matlab/outputs/jimin';
obs = read_snapshot(fullfile(inputDir, 'ndvi_hls_20fields.csv'), ...
    ["field_id", "date", "ndvi", "valid_frac"]);
fields = read_snapshot(fullfile(inputDir, 'fields_20.csv'), "field_id");
assert(height(fields) == numel(unique(fields.field_id)), 'Duplicate fields');
assert(all(ismember(obs.field_id, fields.field_id)), 'Unknown field_id');
obs.date = datetime(obs.date, 'InputFormat', 'yyyy-MM-dd');
assert(~any(isnat(obs.date)), 'Invalid dates');
years = unique(year(obs.date));
assert(~isempty(years) && all(years >= 2013), 'No HLS observations; 2012 unavailable');
season = table('Size', [height(fields)*numel(years), 9], ...
    'VariableTypes', {'string','double','double','double','double','double','double','double','string'}, ...
    'VariableNames', {'field_id','year','greenup_doy','peak_doy','senescence_doy', ...
    'season_length_days','threshold_ndvi','supported_days','status'});
daily = table();
row = 0;
for f = 1:height(fields)
    for y = reshape(years, 1, [])
        row = row + 1;
        dates = (datetime(y,1,1):caldays(1):datetime(y,12,31))';
        raw = nan(numel(dates), 1);
        block = obs(obs.field_id == fields.field_id(f) & year(obs.date) == y, :);
        good = isfinite(block.ndvi) & abs(block.ndvi) <= 1 ...
            & isfinite(block.valid_frac) & block.valid_frac >= 0.5 & block.valid_frac <= 1;
        block = block(good, :);
        [seen, ~, group] = unique(block.date);
        if ~isempty(seen)
            [~, pos] = ismember(seen, dates);
            raw(pos) = accumarray(group, block.ndvi, [], @mean);
        end
        filled = raw;
        known = find(isfinite(raw));
        for k = 1:numel(known)-1
            a = known(k); b = known(k+1);
            if b-a <= 20
                filled(a:b) = interp1([a;b], raw([a;b]), (a:b)', 'linear');
            end
        end
        smoothed = nan(size(raw));
        edges = diff([false; isfinite(filled); false]);
        starts = find(edges == 1); stops = find(edges == -1)-1;
        for k = 1:numel(starts)
            idx = starts(k):stops(k);
            if numel(idx) >= 11
                values = filled(idx);
                n = numel(idx);
                for j = 1:n
                    start = min(max(j-5,1),n-10);
                    window = start:start+10;
                    x = (window-j)';
                    coef = [ones(11,1),x,x.^2] \ values(window);
                    smoothed(idx(j)) = coef(1);
                end
            end
        end
        % Keep leap-day position for civil-day phenology; omit Feb 29 in
        % supported-day counts and engine comparisons, matching hydro.py.
        scored = ~(month(dates) == 2 & day(dates) == 29);
        smoothed(~scored) = NaN;
        supported = isfinite(smoothed);
        green = NaN; peak = NaN; sen = NaN; lengthDays = NaN; threshold = NaN;
        status = "information_gap_no_supported_days";
        if any(supported)
            ix = find(supported);
            [hi, p] = max(smoothed(ix)); peak = ix(p);
            lo = min(smoothed(ix));
            if hi-lo > 1e-6
                threshold = lo + 0.2*(hi-lo);
                rise = find(smoothed(1:end-1) < threshold & smoothed(2:end) >= threshold) + 1;
                fall = find(smoothed(1:end-1) >= threshold & smoothed(2:end) < threshold) + 1;
                rise = rise(rise <= peak); fall = fall(fall > peak);
                if ~isempty(rise), green = rise(end); end
                if ~isempty(fall), sen = fall(1); end
                status = "information_gap_missing_transition";
                if isfinite(green) && isfinite(sen)
                    lengthDays = sen-green;
                    status = "provisional_dominant_peak_screening";
                end
            else
                status = "information_gap_flat_curve";
            end
        end
        season(row,:) = {fields.field_id(f), y, green, peak, sen, lengthDays, ...
            threshold, sum(supported), status};
        d = table(repmat(fields.field_id(f), numel(dates), 1), dates, ...
            repmat(y,numel(dates),1), smoothed, ...
            'VariableNames', {'field_id','date','year','ndvi_smooth'});
        daily = [daily; d]; %#ok<AGROW>
    end
end
paths = {fullfile(outputDir, 'growing_season_20fields.csv'), ...
    fullfile(outputDir, 'jimin_supported_daily.csv')};
archive_existing_outputs(outputDir, paths);
writetable(season, paths{1}, 'Encoding', 'UTF-8');
daily.date.Format = 'yyyy-MM-dd';
writetable(daily, paths{2}, 'Encoding', 'UTF-8');
fprintf('Saved growing-season and supported daily CSVs: %d field-years.\n', height(season));
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
