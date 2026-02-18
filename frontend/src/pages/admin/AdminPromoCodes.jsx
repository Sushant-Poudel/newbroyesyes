import { useEffect, useState } from 'react';
import { Plus, Pencil, Trash2, Ticket, Percent, DollarSign } from 'lucide-react';
import AdminLayout from '@/components/AdminLayout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from 'sonner';
import { promoCodesAPI } from '@/lib/api';

const emptyCode = { code: '', discount_type: 'percentage', discount_value: '', min_order_amount: '', max_uses: '', max_uses_per_user: '', is_active: true };

export default function AdminPromoCodes() {
  const [codes, setCodes] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingCode, setEditingCode] = useState(null);
  const [formData, setFormData] = useState(emptyCode);

  const fetchCodes = async () => {
    try {
      const res = await promoCodesAPI.getAll();
      setCodes(res.data);
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { fetchCodes(); }, []);

  const handleOpenDialog = (code = null) => {
    if (code) {
      setEditingCode(code);
      setFormData({
        code: code.code,
        discount_type: code.discount_type,
        discount_value: code.discount_value,
        min_order_amount: code.min_order_amount || '',
        max_uses: code.max_uses || '',
        max_uses_per_user: code.max_uses_per_customer || code.max_uses_per_user || '',
        is_active: code.is_active
      });
    } else {
      setEditingCode(null);
      setFormData(emptyCode);
    }
    setIsDialogOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.code || !formData.discount_value) {
      toast.error('Code and discount value are required');
      return;
    }
    try {
      const submitData = {
        ...formData,
        discount_value: parseFloat(formData.discount_value),
        min_order_amount: formData.min_order_amount ? parseFloat(formData.min_order_amount) : 0,
        max_uses: formData.max_uses ? parseInt(formData.max_uses) : null,
        max_uses_per_customer: formData.max_uses_per_user ? parseInt(formData.max_uses_per_user) : null
      };
      
      if (editingCode) {
        await promoCodesAPI.update(editingCode.id, submitData);
        toast.success('Promo code updated!');
      } else {
        await promoCodesAPI.create(submitData);
        toast.success('Promo code created!');
      }
      setIsDialogOpen(false);
      fetchCodes();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error saving promo code');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this promo code?')) return;
    try {
      await promoCodesAPI.delete(id);
      toast.success('Promo code deleted!');
      fetchCodes();
    } catch (error) {
      toast.error('Error deleting promo code');
    }
  };

  return (
    <AdminLayout title="Promo Codes">
      <div className="space-y-4 lg:space-y-6" data-testid="admin-promo-codes">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <p className="text-white/60 text-sm lg:text-base">Manage discount codes for customers</p>
          <Button onClick={() => handleOpenDialog()} className="bg-gold-500 hover:bg-gold-600 text-black w-full sm:w-auto" data-testid="add-promo-code-btn">
            <Plus className="h-4 w-4 mr-2" />Add Promo Code
          </Button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 lg:gap-4">
          {isLoading ? (
            [1, 2, 3].map((i) => <div key={i} className="h-28 skeleton rounded-lg"></div>)
          ) : codes.length === 0 ? (
            <div className="col-span-full text-center py-12 bg-card border border-white/10 rounded-lg">
              <Ticket className="h-12 w-12 mx-auto text-white/20 mb-4" />
              <p className="text-white/40 mb-4">No promo codes yet</p>
              <Button onClick={() => handleOpenDialog()} variant="outline" className="border-gold-500 text-gold-500">
                <Plus className="h-4 w-4 mr-2" />Create Your First Promo Code
              </Button>
            </div>
          ) : (
            codes.map((code) => (
              <div key={code.id} className={`bg-card border rounded-lg p-4 hover:border-gold-500/30 transition-all ${code.is_active ? 'border-white/10' : 'border-red-500/30 opacity-60'}`} data-testid={`promo-code-${code.id}`}>
                <div className="flex items-start justify-between gap-2 mb-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-heading font-bold text-gold-500 text-lg tracking-wider">{code.code}</h3>
                      {!code.is_active && <Badge variant="destructive" className="text-xs">Inactive</Badge>}
                    </div>
                    <div className="flex items-center gap-1 mt-1">
                      {code.discount_type === 'percentage' ? (
                        <Percent className="h-4 w-4 text-green-400" />
                      ) : (
                        <DollarSign className="h-4 w-4 text-green-400" />
                      )}
                      <span className="text-green-400 font-semibold">
                        {code.discount_type === 'percentage' ? `${code.discount_value}% OFF` : `Rs ${code.discount_value} OFF`}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-1">
                    <Button variant="ghost" size="sm" onClick={() => handleOpenDialog(code)} className="text-white/60 hover:text-gold-500 p-2">
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => handleDelete(code.id)} className="text-white/60 hover:text-red-500 p-2">
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
                <div className="text-xs text-white/40 space-y-1">
                  {code.min_order_amount > 0 && <p>Min order: Rs {code.min_order_amount}</p>}
                  {code.max_uses && <p>Total uses: {code.used_count || 0} / {code.max_uses}</p>}
                  {(code.max_uses_per_customer || code.max_uses_per_user) && <p>Per user: {code.max_uses_per_customer || code.max_uses_per_user}x</p>}
                </div>
              </div>
            ))
          )}
        </div>

        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogContent className="bg-card border-white/10 text-white max-w-md sm:mx-auto">
            <DialogHeader>
              <DialogTitle className="font-heading text-xl uppercase">
                {editingCode ? 'Edit Promo Code' : 'Add Promo Code'}
              </DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label>Promo Code</Label>
                <Input
                  value={formData.code}
                  onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
                  className="bg-black border-white/20 uppercase font-mono"
                  placeholder="e.g. SAVE20"
                  required
                  data-testid="promo-code-input"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Discount Type</Label>
                  <Select value={formData.discount_type} onValueChange={(value) => setFormData({ ...formData, discount_type: value })}>
                    <SelectTrigger className="bg-black border-white/20">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="percentage">Percentage (%)</SelectItem>
                      <SelectItem value="fixed">Fixed Amount (Rs)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Discount Value</Label>
                  <Input
                    type="number"
                    value={formData.discount_value}
                    onChange={(e) => setFormData({ ...formData, discount_value: e.target.value })}
                    className="bg-black border-white/20"
                    placeholder={formData.discount_type === 'percentage' ? '10' : '100'}
                    required
                    data-testid="promo-discount-input"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Min Order Amount</Label>
                  <Input
                    type="number"
                    value={formData.min_order_amount}
                    onChange={(e) => setFormData({ ...formData, min_order_amount: e.target.value })}
                    className="bg-black border-white/20"
                    placeholder="0"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Max Uses (Total)</Label>
                  <Input
                    type="number"
                    value={formData.max_uses}
                    onChange={(e) => setFormData({ ...formData, max_uses: e.target.value })}
                    className="bg-black border-white/20"
                    placeholder="Unlimited"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label>Max Uses Per User</Label>
                <Input
                  type="number"
                  value={formData.max_uses_per_user}
                  onChange={(e) => setFormData({ ...formData, max_uses_per_user: e.target.value })}
                  className="bg-black border-white/20"
                  placeholder="Unlimited (e.g., 1 = one-time use per user)"
                />
                <p className="text-xs text-white/40">Limit how many times each logged-in user can use this code</p>
              </div>

              <div className="flex items-center gap-2">
                <Switch
                  checked={formData.is_active}
                  onCheckedChange={(checked) => setFormData({ ...formData, is_active: checked })}
                />
                <Label>Active</Label>
              </div>

              <div className="flex flex-col-reverse sm:flex-row justify-end gap-3 pt-2">
                <Button type="button" variant="ghost" onClick={() => setIsDialogOpen(false)} className="w-full sm:w-auto">
                  Cancel
                </Button>
                <Button type="submit" className="bg-gold-500 hover:bg-gold-600 text-black w-full sm:w-auto" data-testid="save-promo-code-btn">
                  {editingCode ? 'Update' : 'Create'} Code
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>
    </AdminLayout>
  );
}
