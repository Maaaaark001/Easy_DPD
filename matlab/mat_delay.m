function x_d = mat_delay(x, d)
% 该函数对x产生d长度的delay
    if d == 0
        x_d = x;
    else
        x_d = circshift(x, d);
        x_d(1:d, 1) = 0;
    end

end
