% run_all_woochan  —  ART FARM: open this file and press Run ▶. That's all.
% Runs every script for woochan in order, logs each result to
% /data/processed/v1/matlab/outputs/woochan/run_log.json (the server reads it and
% either fixes errors automatically or posts your result summary on Mattermost).
% If a <name>_fixed.m exists it is used instead of <name>.m. No need to close/reopen
% files after a server fix: just press Run ▶ again (rehash/clear is done for you).
artfarmUser = 'woochan';
artfarmScripts = {'FieldShift_V8_batch', 'woochan_kc_sensitivity'};
artfarmHere = fileparts(mfilename('fullpath'));
if isempty(artfarmHere)
    artfarmHere = fullfile(getenv('HOME'), 'Documents', 'MATLAB', 'work');
end
cd(artfarmHere);
addpath(artfarmHere);
rehash;
clear artfarm_run_logged;
artfarmLog = [];
for artfarmK = 1:numel(artfarmScripts)
    fprintf('\n[ART FARM] (%d/%d) %s ...\n', artfarmK, numel(artfarmScripts), artfarmScripts{artfarmK});
    artfarmLog = artfarm_run_logged(artfarmScripts{artfarmK}, artfarmUser, artfarmLog, artfarmK == numel(artfarmScripts));
end
fprintf('\n===== ART FARM summary (%s) =====\n', artfarmLog.user);
for artfarmK = 1:numel(artfarmLog.steps)
    artfarmS = artfarmLog.steps{artfarmK};
    if artfarmS.success
        fprintf('  OK    %-28s %6.1f s  %d file(s)\n', artfarmS.resolved, artfarmS.seconds, numel(artfarmS.files));
    else
        fprintf(2, '  FAIL  %-28s %s\n', artfarmS.resolved, artfarmS.error_message);
    end
end
fprintf('Log: /data/processed/v1/matlab/outputs/%s/run_log.json\n', artfarmLog.user);
fprintf('Server will reply in your Mattermost 1:1 room within about a minute.\n');
