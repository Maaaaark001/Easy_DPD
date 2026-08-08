function dis=distortion(x)
%该函数使用saleh模型模拟无记忆失真，使用FIR滤波器模拟记忆效应，
    b = [0.7692 0.1538 0.0769]; %《射频功放数字预失真线性化技术研究_詹鹏》
    a = [1];
    % 检测该模型的AM/AM与AM/PM
    dis=saleh(filter(b, a, x));
end
