% FOR HELICOPTER NR 3-10
% This file contains the initialization for the helicopter assignment in
% the course TTK4115. Run this file before you execute QuaRC_ -> Build 
% to build the file heli_q8.mdl.

% Oppdatert høsten 2006 av Jostein Bakkeheim
% Oppdatert høsten 2008 av Arnfinn Aas Eielsen
% Oppdatert høsten 2009 av Jonathan Ronen
% Updated fall 2010, Dominik Breu
% Updated fall 2013, Mark Haring
% Updated spring 2015, Mark Haring


%%%%%%%%%%% Calibration of the encoder and the hardware for the specific
%%%%%%%%%%% helicopter
Joystick_gain_x = 1;
Joystick_gain_y = -1;


%%%%%%%%%%% Physical constants
g = 9.81; % gravitational constant [m/s^2]
l_c = 0.46; % distance elevation axis to counterweight [m]
l_h = 0.66; % distance elevation axis to helicopter head [m]
l_p = 0.175; % distance pitch axis to motor [m]
m_c = 1.92; % Counterweight mass [kg]
m_p = 0.72; % Motor mass [kg]

K_f = ((2*m_p*l_h - m_c*l_c)*g)/(7.5*l_h);

L_3 = l_h*K_f;
J_e = m_c*l_c^2+2*m_p*l_h^2;

%state-feedback controller
K_1 = K_f/(2*m_p*l_p);
K_2 = L_3/J_e;

lambda1 = 1+1i;
lambda2 = 1-1i;

Kpp = (lambda1*lambda2)/K_1;
Kpd = (-(lambda1 + lambda2))/K_1;

% Without integral
%A = [0 1 0; 0 0 0; 0 0 0];
%B = [0 0; 0 K_1; K_2 0];
%Q = diag([40, 40, 300]);
%R = diag([100, 100]);

%K = lqr(A, B, Q, R);

% Integral
A = [0 1 0 0 0; 0 0 0 0 0; 0 0 0 0 0; -1 0 0 0 0; 0 0 -1 0 0];
B = [0 0; 0 K_1; K_2 0; 0 0; 0 0];
G = [0 0; 0 0; 0 0; 1 0; 0 1];

Q = diag([40, 40, 40, 1, 30]);
R = diag([10, 10]);

K = lqr(A, B, Q, R);

% Lab 3
L_2 = (2*m_p*l_h*g)-(m_c*l_c*g);
Vs_0 = -L_2/L_3;
L_4 = l_h*K_f;
J_l = m_c*l_c^2 + 2*m_p*(l_h^2+l_p^2);
K_3 = (L_4* Vs_0)/J_l;

PORT = 3;
A_e = [0 1 0 0 0; 0 0 0 0 0; 0 0 0 1 0; 0 0 0 0 0; K_3 0 0 0 0];
B_e = [0 0; 0 K_1; 0 0; K_2 0; 0 0];
C_e = [0 0 1 0 0; 0 0 0 0 1];

%%% redigerbar
skalar = 1;
p = skalar*[-3; -6; -3; -10; -2]; %positiv pol = ustabil
%%%

L = place(A_e', C_e', p)';




