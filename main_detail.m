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
sig_in = sig_in / max(sig_in); %输入信号归一化

%% 建立带记忆功放失真模型

u = linspace(0, 1, N);
PA_out_u = distortion(u.');

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

%对输入信号失真
PA_out = distortion(sig_in);
figure(2)
clf
plot(real(PA_out))
hold on
plot(real(sig_in))
hold off
plt_fft(PA_out.', fs, 3, 1);
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
u = u.';
K = 7;
M = 3;

% 拟合测试，判断阶数与记忆深度是否匹配

y_dis = DPD_Func(y, x, u, K, M); %注:由于DPD_Func采用的逆模型，这里检测匹配的时候x与y应反过来
figure(4)
subplot(2, 1, 1)
plot(u, u);
hold on
plot(u, abs(PA_out_u));
hold on
plot(u, abs(y_dis));
hold off;
legend(["line" "PA out" "GMP"])
title("AM/AM")
xlabel("sig in")
ylabel("PA out")
subplot(2, 1, 2)
plot(u, angle(PA_out_u));
hold on
plot(u, angle(y_dis));
hold off
legend(["PA out" "GMP"])
title("AM/PM")
xlabel("sig in")
ylabel("PA out")
hold off;
nmse0 = NMSE(u, PA_out_u);
nmse = NMSE(PA_out_u, y_dis); %归一化均方误差，越接近于0越好

%% 使用逆模型构建预失真

X_pre = DPD_Func(x, y, x, K, M);
PA_out2 = distortion(X_pre);
nmse1 = NMSE(x, PA_out2);
figure(5)
plot(real(PA_out2))
hold on
plot(real(PA_out))
hold off
plt_fft(PA_out2, fs, 6, 1);
ylim([-80 0])
xlim([0 200e3])
ylabel("功率谱")
xlabel("f/Hz")
title("预失真补偿后")

%% 使用新信号观测系数是否具有泛化能力

f4 = 111e3;
f5 = 89e3;
sig_in2 = sin(2 * pi * f4 .* t) + sin(2 * pi * f5 .* t);
sig_in2 = sig_in2 / max(sig_in2); %输入信号归一化
X_pre2 = DPD_Func(x, y, sig_in2.', K, M);
PA_out3 = distortion(X_pre2);
nmse2 = NMSE(x, PA_out3);
plt_fft(PA_out3, fs, 7, 1);
ylim([-80 0])
xlim([0 200e3])
ylabel("功率谱")
xlabel("f/Hz")
title("预失真补偿后")
