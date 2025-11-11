%% Load data saved by Simulink "To File" (Array format)
% The MAT file contains one variable; first row = time, remaining rows = signals.
matPath = 'Test1_1.mat';        % <-- change to your filename
S = load(matPath);

% Get the first (and usually only) variable from the file robustly
fn = fieldnames(S);
A  = S.(fn{1});              % size = (1+numSignals) x N

t  = A(1, :).';              % time (column vector)
Y  = A(2:end, :).';          % signals (N x numSignals), each column a signal

% OPTIONAL: name your channels for legends (edit as needed)
% Assuming x = [p, pdot, e, edot, lambda, lambdadot]
names = {'p','\dot{p}','e','\dot{e}','\lambda','\dot{\lambda}'};
% Pick which columns to plot:
colsToPlot = [1 2 3 4 5 6];          % e.g., p and \dot{p}

%% Figure formatting (same as your template)
width = 10; height = 10; fontsize = 10; x = 20; y = 20;
set(0,'DefaultTextInterpreter','latex');

fig1 = figure(1); clf
fig1.Units = 'centimeters';
fig1.Position = [x y width height];

%% Plot the selected signals
plot(t, Y(:, colsToPlot), 'LineWidth', 1.5); grid on

ax = gca;
ax.FontUnits = 'points';
ax.FontSize = fontsize;
ax.TickLabelInterpreter = 'latex';

xlabel('Time [s]')
ylabel('Value')                    % change if you plot a specific variable
legTxt = names(colsToPlot);
legend(legTxt{:}, 'Location','NorthEast')
title('States over time')
ax.TitleFontSizeMultiplier = 1.1;

%% Optional: custom y-ticks like your template
% ax.YTick = -pi:(pi/2):pi;
% ax.YTickLabel = {'$-\pi$', '$-\frac{\pi}{2}$','$0$','$\frac{\pi}{2}$','$\pi$'};

%% Export (vector PDF preferred for LaTeX)
outDir = 'figs'; if ~exist(outDir,'dir'), mkdir(outDir); end
exportgraphics(fig1, fullfile(outDir,'run1_states.pdf'));   % include with \includegraphics

% If your template insists on EPS:
% hgexport(fig1, fullfile(outDir,'run1_states.eps'))

%%% Lagring
%exportgraphics(gcf, 'lab1test3.pdf', 'ContentType', 'vector', 'BackgroundColor', 'none');