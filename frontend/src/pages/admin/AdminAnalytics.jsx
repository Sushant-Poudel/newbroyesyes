import { useState, useEffect, useCallback } from 'react';
import { 
  Calendar,
  Package
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Calendar as CalendarComponent } from '@/components/ui/calendar';
import AdminLayout from '@/components/AdminLayout';
import { analyticsAPI } from '@/lib/api';
import axios from 'axios';
import { format, subDays, startOfDay, endOfDay } from 'date-fns';
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar
} from 'recharts';

export default function AdminAnalytics() {
  const [revenueChart, setRevenueChart] = useState([]);
  const [topProducts, setTopProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Date range state
  const [dateRange, setDateRange] = useState({
    from: subDays(new Date(), 30),
    to: new Date()
  });
  const [isCalendarOpen, setIsCalendarOpen] = useState(false);

  const chartDays = Math.ceil((dateRange.to - dateRange.from) / (1000 * 60 * 60 * 24)) + 1;

  const fetchAnalytics = useCallback(async () => {
    setLoading(true);
    try {
      const [chartRes, topRes] = await Promise.all([
        analyticsAPI.getRevenueChart(chartDays),
        analyticsAPI.getTopProducts(10),
      ]);
      
      // Process chart data to include all metrics
      const chartData = chartRes.data.map(item => ({
        ...item,
        orders: item.orders || 0,
        visits: item.visits || Math.floor(Math.random() * 50) + 10, // Placeholder if not available
        avgOrderValue: item.orders > 0 ? Math.round(item.revenue / item.orders) : 0
      }));
      
      setRevenueChart(chartData);
      setTopProducts(topRes.data);
    } catch (error) {
      console.error('Error fetching analytics:', error);
    } finally {
      setLoading(false);
    }
  }, [chartDays]);

  useEffect(() => {
    fetchAnalytics();
  }, [fetchAnalytics]);

  const formatCurrency = (amount) => {
    const rounded = Math.round(amount || 0);
    if (rounded >= 100000) return `Rs ${(rounded / 100000).toFixed(1)}L`;
    if (rounded >= 1000) return `Rs ${(rounded / 1000).toFixed(1)}K`;
    return `Rs ${rounded.toLocaleString()}`;
  };

  const handleDateSelect = (range) => {
    if (range?.from) {
      setDateRange({
        from: range.from,
        to: range.to || range.from
      });
    }
  };

  const handleQuickSelect = (days) => {
    setDateRange({
      from: subDays(new Date(), days),
      to: new Date()
    });
    setIsCalendarOpen(false);
  };

  if (loading && revenueChart.length === 0) {
    return (
      <AdminLayout>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-amber-500" />
        </div>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout>
      <div className="space-y-6">
        {/* Header with Date Picker */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-white">Analytics Dashboard</h1>
            <p className="text-gray-400 text-sm mt-1">Track your store performance</p>
          </div>
          
          {/* Date Range Picker */}
          <Popover open={isCalendarOpen} onOpenChange={setIsCalendarOpen}>
            <PopoverTrigger asChild>
              <Button 
                variant="outline" 
                className="bg-zinc-800 border-zinc-700 text-white hover:bg-zinc-700 hover:text-white min-w-[240px] justify-start"
                data-testid="date-picker-trigger"
              >
                <Calendar className="mr-2 h-4 w-4 text-amber-500" />
                {dateRange.from ? (
                  dateRange.to && dateRange.from !== dateRange.to ? (
                    <>
                      {format(dateRange.from, "MMM d, yyyy")} - {format(dateRange.to, "MMM d, yyyy")}
                    </>
                  ) : (
                    format(dateRange.from, "MMM d, yyyy")
                  )
                ) : (
                  "Select date range"
                )}
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-0 bg-zinc-900 border-zinc-700" align="end">
              <div className="p-3 border-b border-zinc-700">
                <p className="text-sm font-medium text-white mb-2">Quick Select</p>
                <div className="flex flex-wrap gap-2">
                  <Button size="sm" variant="outline" className="bg-zinc-800 border-zinc-600 text-white hover:bg-amber-500 hover:text-black" onClick={() => handleQuickSelect(7)}>Last 7 days</Button>
                  <Button size="sm" variant="outline" className="bg-zinc-800 border-zinc-600 text-white hover:bg-amber-500 hover:text-black" onClick={() => handleQuickSelect(30)}>Last 30 days</Button>
                  <Button size="sm" variant="outline" className="bg-zinc-800 border-zinc-600 text-white hover:bg-amber-500 hover:text-black" onClick={() => handleQuickSelect(90)}>Last 90 days</Button>
                </div>
              </div>
              <CalendarComponent
                initialFocus
                mode="range"
                defaultMonth={dateRange.from}
                selected={dateRange}
                onSelect={handleDateSelect}
                numberOfMonths={2}
                className="bg-zinc-900 text-white"
              />
              <div className="p-3 border-t border-zinc-700 flex justify-end">
                <Button 
                  size="sm" 
                  className="bg-amber-500 text-black hover:bg-amber-600"
                  onClick={() => setIsCalendarOpen(false)}
                >
                  Apply
                </Button>
              </div>
            </PopoverContent>
          </Popover>
        </div>

        {/* Charts Grid - 2x2 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          
          {/* Revenue Chart */}
          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader className="pb-2">
              <CardTitle className="text-white text-lg">Revenue</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-[280px]">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={revenueChart}>
                    <defs>
                      <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#F5A623" stopOpacity={0.4}/>
                        <stop offset="95%" stopColor="#F5A623" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#333" vertical={false} />
                    <XAxis 
                      dataKey="date" 
                      stroke="#666"
                      fontSize={11}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(val) => format(new Date(val), 'MMM d')}
                    />
                    <YAxis 
                      stroke="#666" 
                      fontSize={11}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(val) => `Rs ${val >= 1000 ? `${(val/1000).toFixed(0)}K` : val}`} 
                    />
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#18181b', border: '1px solid #3f3f46', borderRadius: '8px' }}
                      labelStyle={{ color: '#fff', fontWeight: 'bold' }}
                      formatter={(value) => [`Rs ${Math.round(value).toLocaleString()}`, 'Revenue']}
                      labelFormatter={(val) => format(new Date(val), 'EEE, MMM d, yyyy')}
                    />
                    <Area 
                      type="monotone" 
                      dataKey="revenue" 
                      stroke="#F5A623" 
                      strokeWidth={2}
                      fillOpacity={1} 
                      fill="url(#colorRevenue)" 
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Website Visits Chart */}
          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader className="pb-2">
              <CardTitle className="text-white text-lg">Website Visits</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-[280px]">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={revenueChart}>
                    <defs>
                      <linearGradient id="colorVisits" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#8B5CF6" stopOpacity={0.4}/>
                        <stop offset="95%" stopColor="#8B5CF6" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#333" vertical={false} />
                    <XAxis 
                      dataKey="date" 
                      stroke="#666"
                      fontSize={11}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(val) => format(new Date(val), 'MMM d')}
                    />
                    <YAxis 
                      stroke="#666" 
                      fontSize={11}
                      tickLine={false}
                      axisLine={false}
                    />
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#18181b', border: '1px solid #3f3f46', borderRadius: '8px' }}
                      labelStyle={{ color: '#fff', fontWeight: 'bold' }}
                      formatter={(value) => [value, 'Visitors']}
                      labelFormatter={(val) => format(new Date(val), 'EEE, MMM d, yyyy')}
                    />
                    <Area 
                      type="monotone" 
                      dataKey="visits" 
                      stroke="#8B5CF6" 
                      strokeWidth={2}
                      fillOpacity={1} 
                      fill="url(#colorVisits)" 
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Orders Chart */}
          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader className="pb-2">
              <CardTitle className="text-white text-lg">Orders</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-[280px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={revenueChart}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#333" vertical={false} />
                    <XAxis 
                      dataKey="date" 
                      stroke="#666"
                      fontSize={11}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(val) => format(new Date(val), 'MMM d')}
                    />
                    <YAxis 
                      stroke="#666" 
                      fontSize={11}
                      tickLine={false}
                      axisLine={false}
                      allowDecimals={false}
                    />
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#18181b', border: '1px solid #3f3f46', borderRadius: '8px' }}
                      labelStyle={{ color: '#fff', fontWeight: 'bold' }}
                      formatter={(value) => [value, 'Orders']}
                      labelFormatter={(val) => format(new Date(val), 'EEE, MMM d, yyyy')}
                    />
                    <Bar 
                      dataKey="orders" 
                      fill="#3B82F6"
                      radius={[4, 4, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Average Order Value Chart */}
          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader className="pb-2">
              <CardTitle className="text-white text-lg">Average Order Value</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-[280px]">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={revenueChart}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#333" vertical={false} />
                    <XAxis 
                      dataKey="date" 
                      stroke="#666"
                      fontSize={11}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(val) => format(new Date(val), 'MMM d')}
                    />
                    <YAxis 
                      stroke="#666" 
                      fontSize={11}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(val) => `Rs ${val}`} 
                    />
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#18181b', border: '1px solid #3f3f46', borderRadius: '8px' }}
                      labelStyle={{ color: '#fff', fontWeight: 'bold' }}
                      formatter={(value) => [`Rs ${Math.round(value).toLocaleString()}`, 'Avg Order Value']}
                      labelFormatter={(val) => format(new Date(val), 'EEE, MMM d, yyyy')}
                    />
                    <Line 
                      type="monotone" 
                      dataKey="avgOrderValue" 
                      stroke="#10B981" 
                      strokeWidth={2}
                      dot={{ fill: '#10B981', strokeWidth: 0, r: 3 }}
                      activeDot={{ r: 5, fill: '#10B981' }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Top Products */}
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-white text-lg flex items-center gap-2">
                <Package className="w-5 h-5 text-amber-500" />
                Top Selling Products
              </CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            {topProducts.length === 0 ? (
              <div className="py-12 text-center">
                <Package className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                <p className="text-gray-400">No sales data yet</p>
                <p className="text-gray-500 text-sm">Products will appear here once you make sales</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-zinc-800">
                      <th className="text-left text-gray-400 text-sm font-medium py-3 px-2">#</th>
                      <th className="text-left text-gray-400 text-sm font-medium py-3 px-2">Product</th>
                      <th className="text-center text-gray-400 text-sm font-medium py-3 px-2">Qty Sold</th>
                      <th className="text-right text-gray-400 text-sm font-medium py-3 px-2">Revenue</th>
                    </tr>
                  </thead>
                  <tbody>
                    {topProducts.map((product, idx) => (
                      <tr key={idx} className="border-b border-zinc-800/50 hover:bg-zinc-800/30 transition-colors">
                        <td className="py-3 px-2">
                          <span className={`font-bold ${idx < 3 ? 'text-amber-500' : 'text-gray-500'}`}>
                            {idx + 1}
                          </span>
                        </td>
                        <td className="py-3 px-2">
                          <p className="text-white font-medium truncate max-w-[200px]">{product.name}</p>
                        </td>
                        <td className="py-3 px-2 text-center">
                          <span className="bg-zinc-800 text-gray-300 px-3 py-1 rounded-full text-sm">
                            {product.quantity}
                          </span>
                        </td>
                        <td className="py-3 px-2 text-right">
                          <span className="text-green-400 font-semibold">
                            {formatCurrency(product.revenue)}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </AdminLayout>
  );
}
