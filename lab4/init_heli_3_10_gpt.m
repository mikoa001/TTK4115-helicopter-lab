function x_hat = fcn(y, u, Ad, Bd, Cd, Rd, Qd)
%#codegen
% y:  [6x1] measurement
% u:  [2x1] input
% Ad: [6x6], Bd: [6x2], Cd: [6x6]
% Rd: [6x6] (use Rh from hover)
% Qd: [6x6] (tunable)

persistent x_bar P_bar I
if isempty(x_bar)
    x_bar = zeros(6,1);
    P_bar = 1e3*eye(6);      % initial covariance
    I     = eye(6);
end

% --- Measurement update ---
S   = Cd*P_bar*Cd' + Rd;     % [6x6]
K   = (P_bar*Cd')/S;         % Kalman gain via solve
innov = y - Cd*x_bar;        % innovation
x_hat = x_bar + K*innov;

% Joseph-form covariance update (numerically safer)
P_hat = (I - K*Cd)*P_bar*(I - K*Cd)' + K*Rd*K';

% --- Time update ---
x_bar = Ad*x_hat + Bd*u;
P_bar = Ad*P_hat*Ad' + Qd;
end




