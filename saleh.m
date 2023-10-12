function y = saleh(x)
    %para = [2.1587 1.1517 4.0033 9.1040];
    para = [1.5 0.5 pi/3 1];
    a1 = para(1); b1 = para(2);
    a2 = para(3); b2 = para(4);
    ain = abs(x);
    thetain = angle(x);
    aout = a1 .* ain ./ (1 + b1 .* ain .^ 2);
    thetapm = a2 * ain .^ 2 ./ (1 + b2 .* ain .^ 2);
    thetaout = thetain + thetapm;
    y = aout .* exp(1j * thetaout);
end
