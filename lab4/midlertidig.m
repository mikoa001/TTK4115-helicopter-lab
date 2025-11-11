T = 0.002;
A = [0 1 0 0 0 0;
     0 0 0 0 0 0;
     0 0 0 1 0 0;
     0 0 0 0 0 0;
     0 0 0 0 0 1;
     K_3 0 0 0 0 0];

B = [0 0;
     0 K_1;
     0 0;
     K_2 0;
     0 0;
     0 0];

C = diag([0,0,1,0,1,0]);
%C = [0 0 1 0 0 0; 0 0 0 0 1 0];
D=0;

sys = ss(A,B,C,D);
sys_d = c2d(sys, T,'zoh');
Ad = sys_d.A;
Bd = sys_d.B;
Cd = sys_d.C;

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Load (replace with your actual variables/paths)
%bruk To Workspace in simulink
size(Y_hover)
size(Y_ground)

% Detrend by mean
Yg = Y_ground - mean(Y_ground,1);
Yh = Y_hover  - mean(Y_hover ,1);

% Experimental covariances (use 1/N normalization so lengths don’t matter)
Rg = cov(Yg, 1);   % ground
Rh = cov(Yh, 1);   % hover  <-- this will be your Rd

% Quick comparison
disp('Diag variances (ground)'); disp(diag(Rg).');
disp('Diag variances (hover)');  disp(diag(Rh).');
disp('Variance ratio hover/ground'); disp((diag(Rh)./diag(Rg)).');

% Check (auto)correlation whiteness per channel
m = size(Yh,2);
maxLag = 100;          % ~ a few hundred ms worth of lags
for i = 1:m
    [acg,lags] = xcorr(Yg(:,i), maxLag, 'biased');
    [ach,~   ] = xcorr(Yh(:,i), maxLag, 'biased');
    figure; subplot(2,1,1); stem(lags, acg./var(Yg(:,i))); grid on;
    title(sprintf('Ground: norm. autocorr y_%d', i));
    subplot(2,1,2); stem(lags, ach./var(Yh(:,i))); grid on;
    title(sprintf('Hover:  norm. autocorr y_%d', i));
end

% Optional: cross-correlation between channels i≠j to reveal coupled noise
% C_ij(l) = xcorr(Y(:,i), Y(:,j), 'biased')




