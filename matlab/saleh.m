function y = saleh(x)
% 该函数为saleh失真模型算法
    para = [1.5 0.5 pi/3 1];%该经验系数比较符合常理
    a1 = para(1); b1 = para(2);
    a2 = para(3); b2 = para(4);
    ain = abs(x);
    thetain = angle(x);
    aout = a1 .* ain ./ (1 + b1 .* ain .^ 2);
    thetapm = a2 * ain .^ 2 ./ (1 + b2 .* ain .^ 2);
    thetaout = thetain + thetapm;
    y = aout .* exp(1j * thetaout);
end
