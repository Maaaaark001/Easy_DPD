function []=plt_fft(x, fs, fl)
% 该函数负责绘制x的fft图像，fl是判断是否归一化的flag，输入1进行归一化
    L = length(x);
    Y = fft(real(x.*hann(L)));
    P2 = abs(Y / L);
    P1 = P2(1:L / 2 + 1);
    P1(2:end - 1) = 2 * P1(2:end - 1);
    f = fs * (0:(L / 2)) / L;
    if fl==1
        P1=20*log10(abs(P1/max(P1)));
    else
        P1=20*log10(abs(P1));
    end

    plot(f, P1)
end
