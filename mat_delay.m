function x_d = mat_delay(x, dd)

    if dd == 0
        x_d = x;
    else
        x_d = circshift(x, dd);
        x_d(1:dd, 1) = 0;
    end

end
