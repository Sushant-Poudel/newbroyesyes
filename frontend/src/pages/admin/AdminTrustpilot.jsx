import { useState } from 'react';
import { Send, Star, CheckCircle, AlertCircle } from 'lucide-react';
import AdminLayout from '@/components/AdminLayout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import { sendTrustpilotInvitation } from '@/lib/api';

export default function AdminTrustpilot() {
  const [formData, setFormData] = useState({
    email: '',
    name: '',
    orderId: '',
    productName: '',
    productUrl: '',
    productImage: '',
  });
  const [isSending, setIsSending] = useState(false);
  const [sentInvitations, setSentInvitations] = useState([]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.email || !formData.name || !formData.orderId) {
      toast.error('Please fill in email, name, and order ID');
      return;
    }

    setIsSending(true);
    
    try {
      const success = sendTrustpilotInvitation({
        email: formData.email,
        name: formData.name,
        orderId: formData.orderId,
        productSlug: formData.orderId,
        productImage: formData.productImage || 'https://via.placeholder.com/150',
        productName: formData.productName || 'Order ' + formData.orderId,
        products: formData.productName ? [{
          sku: formData.orderId,
          productUrl: formData.productUrl || window.location.origin,
          imageUrl: formData.productImage || 'https://via.placeholder.com/150',
          name: formData.productName,
        }] : undefined,
      });

      if (success) {
        toast.success(`Trustpilot invitation sent to ${formData.email}`);
        setSentInvitations([
          { ...formData, sentAt: new Date().toLocaleString() },
          ...sentInvitations.slice(0, 9),
        ]);
        setFormData({
          email: '',
          name: '',
          orderId: '',
          productName: '',
          productUrl: '',
          productImage: '',
        });
      } else {
        toast.error('Trustpilot script not loaded. Please refresh the page.');
      }
    } catch (error) {
      toast.error('Failed to send invitation');
    } finally {
      setIsSending(false);
    }
  };

  return (
    <AdminLayout title="Trustpilot Invitations">
      <div className="space-y-6" data-testid="admin-trustpilot">
        <div className="flex items-center gap-3 text-white/60">
          <Star className="h-5 w-5 text-gold-500" />
          <p className="text-sm">Send review invitations to customers via Trustpilot.</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Send Invitation Form */}
          <div className="bg-card border border-white/10 rounded-lg p-6">
            <h3 className="font-heading text-lg text-white uppercase tracking-wider mb-4 flex items-center gap-2">
              <Send className="h-5 w-5 text-gold-500" />
              Send Invitation
            </h3>
            
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label className="text-white/80">Customer Email *</Label>
                  <Input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="bg-black border-white/20"
                    placeholder="customer@email.com"
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label className="text-white/80">Customer Name *</Label>
                  <Input
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="bg-black border-white/20"
                    placeholder="John Doe"
                    required
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label className="text-white/80">Order/Reference ID *</Label>
                <Input
                  value={formData.orderId}
                  onChange={(e) => setFormData({ ...formData, orderId: e.target.value })}
                  className="bg-black border-white/20"
                  placeholder="ORD-123456"
                  required
                />
              </div>

              <div className="border-t border-white/10 pt-4">
                <p className="text-white/40 text-xs mb-3">Optional - Product Details</p>
                
                <div className="space-y-3">
                  <div className="space-y-2">
                    <Label className="text-white/80">Product Name</Label>
                    <Input
                      value={formData.productName}
                      onChange={(e) => setFormData({ ...formData, productName: e.target.value })}
                      className="bg-black border-white/20"
                      placeholder="Netflix Premium 1 Month"
                    />
                  </div>
                  
                  <div className="space-y-2">
                    <Label className="text-white/80">Product URL</Label>
                    <Input
                      value={formData.productUrl}
                      onChange={(e) => setFormData({ ...formData, productUrl: e.target.value })}
                      className="bg-black border-white/20"
                      placeholder="https://yoursite.com/product/netflix"
                    />
                  </div>
                  
                  <div className="space-y-2">
                    <Label className="text-white/80">Product Image URL</Label>
                    <Input
                      value={formData.productImage}
                      onChange={(e) => setFormData({ ...formData, productImage: e.target.value })}
                      className="bg-black border-white/20"
                      placeholder="https://yoursite.com/images/product.png"
                    />
                  </div>
                </div>
              </div>

              <Button
                type="submit"
                disabled={isSending}
                className="w-full bg-gold-500 hover:bg-gold-600 text-black"
              >
                {isSending ? (
                  <>Sending...</>
                ) : (
                  <>
                    <Send className="h-4 w-4 mr-2" />
                    Send Trustpilot Invitation
                  </>
                )}
              </Button>
            </form>
          </div>

          {/* Recent Invitations */}
          <div className="bg-card border border-white/10 rounded-lg p-6">
            <h3 className="font-heading text-lg text-white uppercase tracking-wider mb-4 flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-green-500" />
              Recent Invitations (This Session)
            </h3>

            {sentInvitations.length === 0 ? (
              <div className="text-center py-8">
                <AlertCircle className="h-10 w-10 text-white/20 mx-auto mb-3" />
                <p className="text-white/40 text-sm">No invitations sent yet in this session.</p>
              </div>
            ) : (
              <div className="space-y-3 max-h-[400px] overflow-y-auto">
                {sentInvitations.map((inv, index) => (
                  <div key={index} className="bg-black/50 rounded-lg p-3 border border-white/5">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0 flex-1">
                        <p className="text-white font-medium text-sm truncate">{inv.name}</p>
                        <p className="text-white/60 text-xs truncate">{inv.email}</p>
                        <p className="text-white/40 text-xs mt-1">Order: {inv.orderId}</p>
                      </div>
                      <div className="text-right flex-shrink-0">
                        <span className="text-green-400 text-xs flex items-center gap-1">
                          <CheckCircle className="h-3 w-3" /> Sent
                        </span>
                        <p className="text-white/40 text-[10px] mt-1">{inv.sentAt}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            <div className="mt-4 pt-4 border-t border-white/10">
              <div className="bg-gold-500/10 border border-gold-500/30 rounded-lg p-3">
                <p className="text-gold-500 text-xs">
                  <strong>Note:</strong> Invitations are sent directly via Trustpilot's JavaScript API. 
                  The customer will receive an email from Trustpilot to leave a review.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </AdminLayout>
  );
}
