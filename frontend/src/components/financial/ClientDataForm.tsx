import { useState } from "react";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Textarea } from "../ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/select";
import { UserPlusIcon } from "lucide-react";

interface ClientData {
  name: string;
  age: number | null;
  income: number | null;
  risk_tolerance: string;
  financial_goals: string;
}

interface ClientDataFormProps {
  onSubmit: (data: ClientData) => void;
  initialData?: Partial<ClientData>;
}

export function ClientDataForm({ onSubmit, initialData = {} }: ClientDataFormProps) {
  const [formData, setFormData] = useState<ClientData>({
    name: initialData.name || "",
    age: initialData.age || null,
    income: initialData.income || null,
    risk_tolerance: initialData.risk_tolerance || "",
    financial_goals: initialData.financial_goals || "",
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(formData);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Client Name */}
      <div className="space-y-2">
        <Label htmlFor="name" className="text-sm font-medium text-gray-200 flex items-center gap-2">
          <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
          Client Name
        </Label>
        <Input
          id="name"
          value={formData.name}
          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          className="bg-gray-800/50 border-gray-600 text-gray-100 placeholder:text-gray-400 focus:border-blue-500 focus:ring-blue-500/20"
          placeholder="Enter client's full name"
          required
        />
      </div>

      {/* Age and Income Row */}
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="age" className="text-sm font-medium text-gray-200 flex items-center gap-2">
            <div className="w-2 h-2 bg-green-500 rounded-full"></div>
            Age
          </Label>
          <Input
            id="age"
            type="number"
            value={formData.age || ""}
            onChange={(e) => setFormData({ ...formData, age: e.target.value ? parseInt(e.target.value) : null })}
            className="bg-gray-800/50 border-gray-600 text-gray-100 placeholder:text-gray-400 focus:border-green-500 focus:ring-green-500/20"
            placeholder="Age"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="income" className="text-sm font-medium text-gray-200 flex items-center gap-2">
            <div className="w-2 h-2 bg-yellow-500 rounded-full"></div>
            Annual Income
          </Label>
          <Input
            id="income"
            type="number"
            step="1000"
            value={formData.income || ""}
            onChange={(e) => setFormData({ ...formData, income: e.target.value ? parseFloat(e.target.value) : null })}
            className="bg-gray-800/50 border-gray-600 text-gray-100 placeholder:text-gray-400 focus:border-yellow-500 focus:ring-yellow-500/20"
            placeholder="$0"
          />
        </div>
      </div>

      {/* Risk Tolerance */}
      <div className="space-y-2">
        <Label htmlFor="risk_tolerance" className="text-sm font-medium text-gray-200 flex items-center gap-2">
          <div className="w-2 h-2 bg-purple-500 rounded-full"></div>
          Risk Tolerance
        </Label>
        <Select
          value={formData.risk_tolerance}
          onValueChange={(value) => setFormData({ ...formData, risk_tolerance: value })}
        >
          <SelectTrigger className="w-full bg-gray-800/50 border-gray-600 text-gray-100 focus:border-purple-500 focus:ring-purple-500/20">
            <SelectValue placeholder="Select risk tolerance" />
          </SelectTrigger>
          <SelectContent className="bg-gray-800 border-gray-600">
            <SelectItem value="conservative" className="text-gray-100 hover:bg-gray-700 focus:bg-gray-700">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                Conservative
              </div>
            </SelectItem>
            <SelectItem value="moderate" className="text-gray-100 hover:bg-gray-700 focus:bg-gray-700">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-yellow-400 rounded-full"></div>
                Moderate
              </div>
            </SelectItem>
            <SelectItem value="aggressive" className="text-gray-100 hover:bg-gray-700 focus:bg-gray-700">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-red-400 rounded-full"></div>
                Aggressive
              </div>
            </SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Financial Goals */}
      <div className="space-y-2">
        <Label htmlFor="financial_goals" className="text-sm font-medium text-gray-200 flex items-center gap-2">
          <div className="w-2 h-2 bg-indigo-500 rounded-full"></div>
          Financial Goals
        </Label>
        <Textarea
          id="financial_goals"
          value={formData.financial_goals}
          onChange={(e) => setFormData({ ...formData, financial_goals: e.target.value })}
          className="bg-gray-800/50 border-gray-600 text-gray-100 placeholder:text-gray-400 focus:border-indigo-500 focus:ring-indigo-500/20 min-h-[80px] resize-none"
          placeholder="Retirement, home purchase, education funding, etc."
        />
      </div>

      {/* Submit Button */}
      <div className="pt-4">
        <Button 
          type="submit" 
          className="w-full bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white font-medium py-3 rounded-xl shadow-lg hover:shadow-xl transition-all duration-200 transform hover:scale-[1.02]"
        >
          <UserPlusIcon className="w-4 h-4 mr-2" />
          Create Client Profile
        </Button>
      </div>
    </form>
  );
}