import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip } from "recharts";

interface NetWorthChartProps {
  data: {
    assets: { totalAssets: number };
    liabilities: { totalLiabilities: number };
    netWorth: number;
  };
}

export const NetWorthChart = ({ data }: NetWorthChartProps) => {
  const chartData = [
    {
      category: "Assets",
      value: data.assets.totalAssets,
      fill: "hsl(var(--success))"
    },
    {
      category: "Liabilities", 
      value: data.liabilities.totalLiabilities,
      fill: "hsl(var(--warning))"
    },
    {
      category: "Net Worth",
      value: data.netWorth,
      fill: "hsl(var(--primary))"
    }
  ];

  const CustomTooltip = ({ active, payload, label }: { active?: boolean; payload?: any[]; label?: string }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-card border border-border rounded-lg p-3 shadow-lg">
          <p className="font-semibold text-foreground">{label}</p>
          <p className="text-sm">
            <span className="font-medium">Amount: </span>
            <span className="font-bold text-primary">${payload[0].value.toLocaleString()}</span>
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <Card className="shadow-[var(--shadow-card)]">
      <CardHeader>
        <CardTitle className="text-primary">Net Worth Overview</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis 
              dataKey="category" 
              stroke="hsl(var(--muted-foreground))"
              fontSize={12}
            />
            <YAxis 
              stroke="hsl(var(--muted-foreground))"
              fontSize={12}
              tickFormatter={(value: number) => `$${value.toLocaleString()}`}
            />
            <Tooltip content={<CustomTooltip />} />
            <Bar 
              dataKey="value" 
              radius={[4, 4, 0, 0]}
              fill="hsl(var(--primary))"
            />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
};
