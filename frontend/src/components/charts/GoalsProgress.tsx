import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Progress } from "../ui/progress";
import { Badge } from "../ui/badge";

interface Goal {
  goal: string;
  amount: number;
  progress: number;
}

interface GoalsProgressProps {
  data: {
    shortTerm: Goal[];
    mediumTerm: Goal[];
    longTerm: Goal[];
  };
}

export const GoalsProgress = ({ data }: GoalsProgressProps) => {
  const renderGoalSection = (goals: Goal[], title: string, variant: "default" | "secondary" | "outline") => (
    <div className="space-y-4">
      <Badge variant={variant} className="mb-2">{title}</Badge>
      {goals.map((goal, index) => (
        <div key={index} className="p-4 bg-secondary rounded-lg space-y-3">
          <div className="flex justify-between items-center">
            <h4 className="font-medium text-foreground text-sm">{goal.goal}</h4>
            <span className="text-xs text-muted-foreground">
              Target: ${goal.amount.toLocaleString()}
            </span>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-xs text-muted-foreground">Progress</span>
              <span className="text-xs font-semibold text-primary">{goal.progress}%</span>
            </div>
            <Progress value={goal.progress} className="h-2" />
            <div className="text-xs text-muted-foreground">
              Current: ${((goal.amount * goal.progress) / 100).toLocaleString()} | 
              Remaining: ${(goal.amount - (goal.amount * goal.progress) / 100).toLocaleString()}
            </div>
          </div>
        </div>
      ))}
    </div>
  );

  return (
    <Card className="shadow-[var(--shadow-card)]">
      <CardHeader>
        <CardTitle className="text-primary">Financial Goals Progress</CardTitle>
        <p className="text-sm text-muted-foreground">Track progress towards short, medium, and long-term objectives</p>
      </CardHeader>
      <CardContent className="space-y-6">
        {renderGoalSection(data.shortTerm, "Short-Term (0-3 years)", "default")}
        {renderGoalSection(data.mediumTerm, "Medium-Term (3-10 years)", "secondary")}
        {renderGoalSection(data.longTerm, "Long-Term (10+ years)", "outline")}
        
        <div className="mt-6 p-4 bg-accent/10 rounded-lg border border-accent/20">
          <h4 className="font-semibold text-foreground mb-2">Recommendations</h4>
          <div className="space-y-1 text-sm text-muted-foreground">
            <p>• Prioritize high-interest debt elimination (car loan)</p>
            <p>• Increase RESP contributions for tax benefits</p>
            <p>• Consider ESG investment options as requested</p>
            <p>• Review retirement timeline and required savings rate</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
