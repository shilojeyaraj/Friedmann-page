import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip } from "recharts";

interface AccountsChartProps {
  data: {
    assets: {
      rrsp: number;
      tfsa: number;
      investments: number;
      realEstate: number;
    };
  };
}

export const AccountsChart = ({ data }: AccountsChartProps) => {
  const chartData = [
    {
      account: "RRSP",
      balance: data.assets.rrsp,
      fill: "hsl(var(--primary))"
    },
    {
      account: "TFSA", 
      balance: data.assets.tfsa,
      fill: "hsl(var(--success))"
    },
    {
      account: "Investment",
      balance: data.assets.investments,
      fill: "hsl(var(--accent))"
    }
  ];

  const CustomTooltip = ({ active, payload, label }: { active?: boolean; payload?: any[]; label?: string }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-card border border-border rounded-lg p-3 shadow-lg">
          <p className="font-semibold text-foreground">{label} Account</p>
          <p className="text-sm">
            <span className="font-medium">Balance: </span>
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
        <CardTitle className="text-primary">Registered & Investment Accounts</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis 
              dataKey="account" 
              stroke="hsl(var(--muted-foreground))"
              fontSize={12}
            />
            <YAxis 
              stroke="hsl(var(--muted-foreground))"
              fontSize={12}
              tickFormatter={(value: number) => `$${(value / 1000).toFixed(0)}K`}
            />
            <Tooltip content={<CustomTooltip />} />
            <Bar 
              dataKey="balance" 
              radius={[4, 4, 0, 0]}
              fill="hsl(var(--primary))"
            />
          </BarChart>
        </ResponsiveContainer>
        <div className="mt-4 grid grid-cols-3 gap-4 text-center">
          <div>
            <p className="text-xs text-muted-foreground">RRSP Contribution</p>
            <p className="font-semibold text-primary">$9,000/year</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">TFSA Contribution</p>
            <p className="font-semibold text-success">$6,500/year</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Total Liquid Assets</p>
            <p className="font-semibold text-accent">
              ${(data.assets.rrsp + data.assets.tfsa + data.assets.investments).toLocaleString()}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
