function [Y] = MP_model(x_i, K, M)
% 该函数为简化记忆多项式矩阵构造
for m=0:M
    x=mat_delay(x_i, m);
    for k=0:K
        if k==0
            H=x;
        else
            H=[H,x.*(abs(x).^k)];
        end
    end
    if m==0
        Y=H;
    else
        Y=[Y,H];
    end
end




end
