function result = jimin_bare_vs_rye()
% Observed supported low NDVI vs engine calendar assumptions, NOT validation.
% Low NDVI <0.3 is provisional, not proof of bare soil or rye identification.
% Calendar scenario for each crop assumes successful rye in previous fall.
% No year/phase is inferred from baseline_rotation. Residue != living cover.
inputDir = '/data/processed/v1/matlab/inputs';
outputDir = '/data/processed/v1/matlab/outputs/jimin';
if ~isfile(fullfile(outputDir, 'jimin_supported_daily.csv'))
    jimin_growing_season;
end
d = read_snapshot(fullfile(outputDir, 'jimin_supported_daily.csv'), ...
    ["field_id", "date", "year", "ndvi_smooth"]);
d.date = datetime(d.date, 'InputFormat', 'yyyy-MM-dd');
assert(~isempty(d) && all(d.year >= 2013), 'HLS cannot observe 2012');
a = read_snapshot(fullfile(inputDir, 'engine_strategyB_assumptions.csv'), ...
    ["field_id", "item", "value", "unit", "source", "run_id"]);
assert(height(unique(a(:, {'field_id','item'}), 'rows')) == height(a), 'Duplicate assumption key');
keys = unique(d(:, {'field_id','year'}), 'rows');
result = table();
for k = 1:height(keys)
    b = d(d.field_id == keys.field_id(k) & d.year == keys.year(k), :);
    scored = ~(month(b.date) == 2 & day(b.date) == 29);
    supported = isfinite(b.ndvi_smooth) & scored;
    winter = month(b.date) <= 4 | month(b.date) >= 11;
    low = supported & b.ndvi_smooth < 0.3;
    observed = NaN; winterObserved = NaN;
    if any(supported), observed = sum(low); end
    if any(supported & winter), winterObserved = sum(low & winter); end
    for crop = ["corn", "soy"]
        items = [crop+"_plant_doy", crop+"_harvest_doy", ...
            "rye_plant_after_harvest_days", "rye_terminate_before_plant_days"];
        values = nan(1,4); sources = strings(1,4); runs = strings(1,4);
        for j = 1:4
            hit = a.field_id == keys.field_id(k) & a.item == items(j);
            if sum(hit) == 1
                values(j) = str2double(string(a.value(hit)));
                sources(j) = a.source(hit); runs(j) = a.run_id(hit);
                assert(a.unit(hit) == "day (365-day engine calendar)", 'Unexpected calendar unit');
            end
        end
        springEnd = NaN; fallStart = NaN;
        assumed = NaN; overlap = NaN; status = "information_gap_missing_calendar";
        if all(isfinite(values)) && all(strlength(sources) > 0) && all(strlength(runs) > 0)
            p = values(1); h = values(2); after = values(3); before = values(4);
            assert(all(values == fix(values)) && p >= 1 && p <= h && h <= 365 ...
                && after >= 1 && before >= 1 && p-before >= 1 && h+after <= 365, 'Invalid calendar');
            % hydro._year_arrays put() uses INCLUSIVE interval endpoints:
            % spring rye [1,p-before], cash [p,h], fall rye [h+after,365].
            doy365 = day(b.date, 'dayofyear') - double(leap_year(keys.year(k)) & month(b.date) > 2);
            living = doy365 <= p-before | (doy365 >= p & doy365 <= h) | doy365 >= h+after;
            springEnd = p-before; fallStart = h+after;
            assumed = (before-1)+(after-1);
            if any(supported), overlap = sum(supported & ~living); end
            status = "calendar_scenario_assumption_not_observed_rye";
        end
        % Terminated residue surface fraction is NOT living rye cover.
        residueFraction = NaN; residueSource = "";
        hit = a.field_id == keys.field_id(k) & a.item == "rye_residue_cover_frac";
        if any(hit)
            assert(a.unit(hit) == "fraction", 'Unexpected residue fraction unit');
            residueFraction = str2double(string(a.value(hit)));
            residueSource = a.source(hit);
            assert(isnan(residueFraction) || (isfinite(residueFraction) ...
                && residueFraction >= 0 && residueFraction <= 1), 'Invalid residue fraction');
        end
        rotation = "";
        hit = a.field_id == keys.field_id(k) & a.item == "baseline_rotation";
        if any(hit), rotation = string(a.value(hit)); end
        r = table(keys.field_id(k), keys.year(k), crop, observed, winterObserved, ...
            sum(supported), sum(supported)/365, assumed, overlap, ...
            strjoin(unique(sources), ";"), strjoin(unique(runs), ";"), rotation, springEnd, fallStart, ...
            residueFraction, residueSource, status, ...
            'VariableNames', {'field_id','year','calendar_crop','observed_low_ndvi_days', ...
            'observed_winter_low_ndvi_days','supported_days','coverage', ...
            'assumed_no_living_cover_days','assumed_no_living_cover_on_supported_days', ...
            'assumption_sources','run_ids','baseline_rotation', ...
            'rye_spring_end_doy','rye_fall_start_doy','rye_residue_cover_frac', ...
            'residue_fraction_source','status'});
        result = [result; r]; %#ok<AGROW>
    end
end
paths = {fullfile(outputDir, 'bare_vs_strategyB.csv'), ...
    fullfile(outputDir, 'jimin_strategyB_assumptions_used.csv')};
archive_existing_outputs(outputDir, paths);
writetable(result, paths{1}, 'Encoding', 'UTF-8');
% Preserve ALL long-form rows, including raw crop_calendar, baseline_rotation,
% residue fraction and provenance. Residue fraction never becomes days.
writetable(a, paths{2}, 'Encoding', 'UTF-8');
fprintf('Saved %s; partial observations and assumptions are separate.\n', paths{1});
end

function yes = leap_year(y)
yes = mod(y,4) == 0 && (mod(y,100) ~= 0 || mod(y,400) == 0);
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
