function x_pre = DPD_Func(x, y, u, K, M)
% 该函数为DPD系数的核心算法
% x:学习样本中系统的输入向量,y:学习样本中系统的输出失真,
% u:目标输出,K:阶数,M:记忆深度
%     x = x.';
%     y = y.';
%     u = u.';
    U = MP_model(u, K, M);
    Y = MP_model(y, K, M);

    Y_H = Y';
    w = pinv(Y_H * Y) * Y_H * x;
    x_pre = U * w;

end
