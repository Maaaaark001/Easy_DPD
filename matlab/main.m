% 部分函数已被重构，请直接查看main_detail.m
%% 信号产生
fs = 1e6;
f1 = 90e3;
f2 = 100e3;
f3 = 110e3;
N = 1024 * 16;
N_FFT = N;
tmax = N / fs;
t = linspace(0, tmax, N);
sig_in = sin(2 * pi * f1 .* t) + sin(2 * pi * f2 .* t) + sin(2 * pi * f3 .* t);
sig_in = sig_in / max(sig_in);

%% 建立带记忆功放失真模型
b = [0.7692 0.1538 0.0769]; %《射频功放数字预失真线性化技术研究_詹鹏》
a = [1];
% 使用saleh模型模拟无记忆失真，使用FIR滤波器模拟记忆效应，检测该模型的AM/AM与AM/PM
u = linspace(0, 1, N);
PA_out_u = saleh(filter(b, a, u));

figure(1)
subplot(2, 1, 1)
plot(u, abs(PA_out_u));
hold on
plot(u, u);
hold off;
title("AM/AM")
xlabel("sig in")
ylabel("PA out")
subplot(2, 1, 2)
plot(u, angle(PA_out_u));
title("AM/PM")
xlabel("sig in")
ylabel("PA out")

PA_out = saleh(filter(b, a, sig_in));
figure(2)
clf
plot(real(PA_out))
hold on
plot(real(sig_in))
hold off
figure(3)
plt_fft(PA_out', fs, 1);
ylim([-80 0])
xlim([0 200e3])
ylabel("功率谱")
xlabel("f/Hz")
title("预失真补偿前")

%% 建立预失真
x = sig_in;
y = PA_out;
x = x.';
y = y.';
K = 7;
M = 3;

X = MP_model(x, K, M);
Y = MP_model(y, K, M);

% 拟合测试，判断阶数与记忆深度是否匹配
U = MP_model(u.', K, M);
X_H = X';
w_test = pinv(X_H * X) * X_H * y;
y_dis = U * w_test;
figure(6)
subplot(2, 1, 1)
plot(u, u);
hold on
plot(u, abs(PA_out_u));
hold on
plot(u, abs(y_dis));
hold off;
legend(["line" "PA_out_u" "GMP_u"])
title("AM/AM")
xlabel("sig in")
ylabel("PA out")
subplot(2, 1, 2)
plot(u, angle(PA_out_u));
hold on
plot(u, angle(y_dis));
hold off
legend(["PA_out_u" "GMP_u"])
title("AM/PM")
xlabel("sig in")
ylabel("PA out")
hold off;



%% 使用逆模型构建预失真
Y_H = Y';
w = pinv(Y_H * Y) * Y_H * x;
X_pre = X * w;
PA_out2 = saleh(filter(b, a, X_pre));

figure(4)
plot(real(PA_out2))
hold on
plot(real(PA_out))
hold off
figure(5)
plt_fft(PA_out2, fs, 1);
ylim([-80 0])
xlim([0 200e3])
ylabel("功率谱")
xlabel("f/Hz")
title("预失真补偿后")
