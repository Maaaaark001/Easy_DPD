function []=plt_fft(x, fs, num,t1)
    L = length(x);
    Y = fft(real(x.*hann(L)));
    P2 = abs(Y / L);
    P1 = P2(1:L / 2 + 1);
    P1(2:end - 1) = 2 * P1(2:end - 1);
    f = fs * (0:(L / 2)) / L;
    if t1==1
        P1=20*log10(abs(P1/max(P1)));
    else
        P1=20*log10(abs(P1));
    end
    figure(num)
    plot(f, P1)
end
