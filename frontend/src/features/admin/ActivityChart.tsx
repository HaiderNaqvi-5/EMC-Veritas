import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export default function ActivityChart({ data }: { data: { status: string; count: number }[] }) {
  return <div className="mt-6 h-56"><ResponsiveContainer width="100%" height="100%"><BarChart data={data}><XAxis dataKey="status"/><YAxis allowDecimals={false}/><Tooltip/><Bar dataKey="count" fill="#4f46e5" radius={[4, 4, 0, 0]}/></BarChart></ResponsiveContainer></div>;
}
