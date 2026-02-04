% Assume you already have your data as vectors
% Example data (replace with your own)
x = [255 245 235 225 215 205 195 185 175 165 155 145 135 125 115 105 95 85 75 65 55 45 35 25 15 10 0];
y = [160 150 140 130 120 100 84 70 55 49 47 44 40 35 33 30 28 25 23 21 20 18 12 8 6 3 0];

% Fit a quadratic polynomial (degree = 3)
p = polyfit(x, y, 3);   

% p is a vector of coefficients [a b c]
%   →  y ≈ a*x^3 + bx^2 + cx + d
disp('3rd polynomial coefficients [a b c d]:');
format long;
disp(p);

% Create smooth points for plotting the fit
x_fit = linspace(min(x), max(x), 200);     % smooth x values
y_fit = polyval(p, x_fit);                 % evaluate polynomial

% Plot
figure;
plot(x, y, 'o', 'MarkerFaceColor','b', 'MarkerSize',8);  hold on;
plot(x_fit, y_fit, 'r-', 'LineWidth', 2.5);
hold off;
xlabel('x'); ylabel('y');
title('Quadratic Regression');
legend('Data', 'polynomial fit', 'Location','best');
grid on;