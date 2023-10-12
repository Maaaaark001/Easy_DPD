function x_pre = DPD_Func(x, y, u, K, M)
%     x = x.';
%     y = y.';
%     u = u.';
    U = MP_model(u, K, M);
    Y = MP_model(y, K, M);

    Y_H = Y';
    w = pinv(Y_H * Y) * Y_H * x;
    x_pre = U * w;

end
