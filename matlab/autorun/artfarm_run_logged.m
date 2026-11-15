function L = artfarm_run_logged(scriptName, user, L, isLast)
%ARTFARM_RUN_LOGGED Run one MATLAB script/function by name and log the result.
%   L = artfarm_run_logged(scriptName, user, L, isLast)
%   - runs scriptName (prefers <name>_fixed.m if present) after rehash/clear,
%   - records start/end time, success, full error report, created/modified files
%     in /data/processed/v1/matlab/outputs/<user>/ (CSV rows, PNG bytes),
%   - saves figures left open as fig_<script>_<n>.png and closes them,
%   - writes outputs/<user>/run_log.json (latest run) and appends one line to
%     outputs/<user>/run_history.jsonl.
%   Never throws: every failure (including logging failures) is caught.
if nargin < 3, L = []; end
if nargin < 4, isLast = true; end
outDir = fullfile('/data/processed/v1/matlab/outputs', user);
step = struct('script', scriptName, 'resolved', '', 'kind', '', 'started', ar_now(), ...
    'ended', '', 'seconds', NaN, 'success', false, 'error_id', '', 'error_message', '', ...
    'error_report', '', 'files', {{}}, 'figures', {{}}, 'output_tail', '');
try
    if isempty(L) || ~isstruct(L)
        L = struct('user', user, 'run_id', char(datetime('now', 'Format', 'yyyyMMdd_HHmmss')), ...
            'started', ar_now(), 'updated', '', 'complete', false, 'matlab_version', version, ...
            'host_cwd', pwd, 'steps', {{}});
    end
    if ~isfolder(outDir), mkdir(outDir); end
    before = ar_snapshot(outDir);
    figsBefore = findall(0, 'Type', 'figure');
    cwd0 = pwd;
    name = ar_resolve(scriptName);
    step.resolved = name;
    diaryFile = [tempname '.txt'];
    t0 = tic;
    try
        diary(diaryFile); diary on;
        rehash;
        clear(name);
        try
            nargin(name);            % errors for scripts
            step.kind = 'function';
            feval(name);
        catch kindErr
            if strcmp(step.kind, 'function'), rethrow(kindErr); end
            step.kind = 'script';
            evalin('base', name);
        end
        step.success = true;
    catch ME
        step.success = false;
        step.error_id = ME.identifier;
        step.error_message = ME.message;
        step.error_report = getReport(ME, 'extended', 'hyperlinks', 'off');
        fprintf(2, '[ART FARM] %s failed: %s\n', name, ME.message);
    end
    diary off;
    step.seconds = toc(t0);
    step.ended = ar_now();
    cd(cwd0);
    try
        txt = fileread(diaryFile); delete(diaryFile);
        if numel(txt) > 4000, txt = txt(end-3999:end); end
        step.output_tail = txt;
    catch
    end
    % Save figures created during this step, then close them.
    figs = findall(0, 'Type', 'figure');
    isNew = true(size(figs));
    for k = 1:numel(figs)
        isNew(k) = ~any(figsBefore == figs(k));
    end
    figs = figs(isNew);
    for k = 1:numel(figs)
        try
            [~, base] = fileparts(name);
            png = fullfile(outDir, sprintf('fig_%s_%d.png', base, k));
            if exist('exportgraphics', 'file')
                exportgraphics(figs(k), png, 'Resolution', 150);
            else
                saveas(figs(k), png);
            end
            step.figures{end+1} = png;
        catch
        end
        try, close(figs(k)); catch, end
    end
    step.files = ar_changes(outDir, before);
catch outer
    step.success = false;
    if isempty(step.error_message)
        step.error_message = ['logger: ' outer.message];
        step.error_report = getReport(outer, 'extended', 'hyperlinks', 'off');
    end
    step.ended = ar_now();
end
try
    if isempty(L) || ~isstruct(L)
        L = struct('user', user, 'run_id', 'unknown', 'started', step.started, 'updated', '', ...
            'complete', false, 'matlab_version', '', 'host_cwd', '', 'steps', {{}});
    end
    L.steps{end+1} = step;
    L.updated = ar_now();
    L.complete = logical(isLast);
    if ~isfolder(outDir), mkdir(outDir); end
    ar_write(fullfile(outDir, 'run_log.json'), jsonencode(L), 'w');
    hist = step; hist.user = user; hist.run_id = L.run_id;
    ar_write(fullfile(outDir, 'run_history.jsonl'), [jsonencode(hist) newline], 'a');
    if step.success
        fprintf('[ART FARM] OK   %s (%.1f s, %d files)\n', step.resolved, step.seconds, numel(step.files));
    end
catch logErr
    fprintf(2, '[ART FARM] could not write run log: %s\n', logErr.message);
end
end

function t = ar_now()
t = char(datetime('now', 'TimeZone', 'UTC', 'Format', 'yyyy-MM-dd''T''HH:mm:ss''Z'''));
end

function name = ar_resolve(name)
name = regexprep(name, '\.m$', '');
while isfile([name '_fixed.m'])
    name = [name '_fixed'];
end
end

function s = ar_snapshot(outDir)
s = containers.Map('KeyType', 'char', 'ValueType', 'double');
d = dir(fullfile(outDir, '**', '*'));
for k = 1:numel(d)
    if ~d(k).isdir
        s(fullfile(d(k).folder, d(k).name)) = d(k).datenum;
    end
end
end

function files = ar_changes(outDir, before)
files = {};
d = dir(fullfile(outDir, '**', '*'));
for k = 1:numel(d)
    if d(k).isdir, continue; end
    p = fullfile(d(k).folder, d(k).name);
    if any(strcmp(d(k).name, {'run_log.json', 'run_history.jsonl'})), continue; end
    if contains(p, [filesep 'old' filesep]), continue; end
    if isKey(before, p) && before(p) == d(k).datenum, continue; end
    f = struct('path', p, 'bytes', d(k).bytes, 'rows', NaN);
    if endsWith(lower(p), '.csv')
        try
            f.rows = height(readtable(p));
        catch
        end
    end
    files{end+1} = f; %#ok<AGROW>
end
end

function ar_write(p, txt, mode)
fid = fopen(p, mode, 'n', 'UTF-8');
if fid < 0, error('artfarm:write', 'cannot open %s', p); end
c = onCleanup(@() fclose(fid));
fprintf(fid, '%s', txt);
end
