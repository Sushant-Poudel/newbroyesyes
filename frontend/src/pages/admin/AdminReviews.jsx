import { useEffect, useState, useCallback } from 'react';
import { Plus, Pencil, Trash2, Star, CheckCircle, XCircle, Clock, MessageSquare, Gift, Download } from 'lucide-react';
import AdminLayout from '@/components/AdminLayout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { toast } from 'sonner';
import { reviewsAPI } from '@/lib/api';

const emptyReview = { reviewer_name: '', rating: 5, comment: '', review_date: '' };

// Draw a 5-point star on canvas
function drawStar(ctx, cx, cy, outerR, innerR) {
  ctx.beginPath();
  for (let i = 0; i < 10; i++) {
    const r = i % 2 === 0 ? outerR : innerR;
    const angle = (Math.PI / 2) * -1 + (Math.PI / 5) * i;
    const x = cx + r * Math.cos(angle);
    const y = cy + r * Math.sin(angle);
    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  }
  ctx.closePath();
  ctx.fill();
}

export default function AdminReviews() {
  const [reviews, setReviews] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingReview, setEditingReview] = useState(null);
  const [formData, setFormData] = useState(emptyReview);
  const [filter, setFilter] = useState('all');
  const [rewardEnabled, setRewardEnabled] = useState(true);
  const [rewardPct, setRewardPct] = useState(5);
  const [savingReward, setSavingReward] = useState(false);

  const fetchReviews = async () => {
    try {
      const res = await reviewsAPI.getAdmin();
      setReviews(res.data);
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { 
    fetchReviews(); 
    fetchRewardSettings();
  }, []);

  const fetchRewardSettings = async () => {
    try {
      const res = await reviewsAPI.getRewardSettings();
      setRewardEnabled(res.data.review_reward_enabled ?? true);
      setRewardPct(res.data.review_reward_percentage ?? 5);
    } catch (e) {}
  };

  const saveRewardSettings = async () => {
    setSavingReward(true);
    try {
      await reviewsAPI.updateRewardSettings({ review_reward_enabled: rewardEnabled, review_reward_percentage: rewardPct });
      toast.success('Reward settings saved!');
    } catch (e) {
      toast.error('Failed to save');
    } finally {
      setSavingReward(false);
    }
  };

  // Generate review image for sharing
  const downloadReviewImage = useCallback((review) => {
    const canvas = document.createElement('canvas');
    const W = 1080, H = 1080;
    canvas.width = W;
    canvas.height = H;
    const ctx = canvas.getContext('2d');

    // White background
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, W, H);

    // Compute aggregate stats for footer
    const approvedReviews = reviews.filter(r => r.status === 'approved' || !r.status);
    const totalReviews = approvedReviews.length;
    const avgRating = totalReviews > 0 ? (approvedReviews.reduce((a, r) => a + r.rating, 0) / totalReviews).toFixed(1) : '5.0';

    // Quote text
    const comment = `\u201C${review.comment}\u201D`;
    ctx.fillStyle = '#111111';
    ctx.font = 'bold 52px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
    ctx.textAlign = 'left';

    // Word-wrap quote
    const maxW = W - 160;
    const words = comment.split(' ');
    const lines = [];
    let line = '';
    for (const word of words) {
      const test = line ? line + ' ' + word : word;
      if (ctx.measureText(test).width > maxW && line) {
        lines.push(line);
        line = word;
      } else {
        line = test;
      }
    }
    if (line) lines.push(line);

    // Center vertically (above stars)
    const lineH = 68;
    const textBlockH = lines.length * lineH;
    const starsY = 620;
    const startY = Math.max(80, (starsY - textBlockH) / 2 + 40);

    lines.forEach((l, i) => {
      ctx.fillText(l, 80, startY + i * lineH);
    });

    // Stars
    const starSize = 44;
    const starGap = 8;
    const starsStartX = 80;
    for (let i = 0; i < 5; i++) {
      const x = starsStartX + i * (starSize + starGap);
      ctx.fillStyle = i < review.rating ? '#F5A623' : '#e0e0e0';
      drawStar(ctx, x + starSize / 2, starsY + starSize / 2, starSize / 2, starSize / 4);
    }

    // "by [Name]"
    const nameX = starsStartX + 5 * (starSize + starGap) + 16;
    ctx.fillStyle = '#555555';
    ctx.font = '36px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
    ctx.fillText(`by ${review.reviewer_name}`, nameX, starsY + 35);

    // Separator line
    const sepY = starsY + 80;
    ctx.strokeStyle = '#e5e5e5';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(80, sepY);
    ctx.lineTo(W - 80, sepY);
    ctx.stroke();

    // Footer: "Rated X.X / 5 | N reviews"
    ctx.fillStyle = '#333333';
    ctx.font = '32px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
    ctx.fillText(`Rated ${avgRating} / 5  |  ${totalReviews} reviews`, 80, sepY + 55);

    // Brand: star icon + "GameShop Nepal"
    const brandY = sepY + 110;
    ctx.fillStyle = '#F5A623';
    drawStar(ctx, 95, brandY, 16, 8);
    ctx.fillStyle = '#333333';
    ctx.font = 'bold 30px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
    ctx.fillText('GameShop Nepal', 120, brandY + 10);

    // "gameshopnepal.com" below brand
    ctx.fillStyle = '#999999';
    ctx.font = '24px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
    ctx.fillText('gameshopnepal.com', 80, brandY + 55);

    // Download
    const link = document.createElement('a');
    link.download = `review-${review.reviewer_name.replace(/\s+/g, '-').toLowerCase()}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
    toast.success('Review image downloaded!');
  }, [reviews]);

  const handleOpenDialog = (review = null) => {
    if (review) { 
      setEditingReview(review); 
      setFormData({ 
        reviewer_name: review.reviewer_name, 
        rating: review.rating, 
        comment: review.comment, 
        review_date: review.review_date ? review.review_date.split('T')[0] : '' 
      }); 
    } else { 
      setEditingReview(null); 
      setFormData(emptyReview); 
    }
    setIsDialogOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.reviewer_name || !formData.comment) { 
      toast.error('Name and comment are required'); 
      return; 
    }
    try {
      const submitData = { 
        ...formData, 
        review_date: formData.review_date ? new Date(formData.review_date).toISOString() : new Date().toISOString() 
      };
      if (editingReview) { 
        await reviewsAPI.update(editingReview.id, submitData); 
        toast.success('Review updated!'); 
      } else { 
        await reviewsAPI.create(submitData); 
        toast.success('Review created!'); 
      }
      setIsDialogOpen(false);
      fetchReviews();
    } catch (error) { 
      toast.error(error.response?.data?.detail || 'Error saving review'); 
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this review?')) return;
    try { 
      await reviewsAPI.delete(id); 
      toast.success('Review deleted!'); 
      fetchReviews(); 
    } catch (error) { 
      toast.error('Error deleting review'); 
    }
  };

  const handleStatusChange = async (id, status) => {
    try {
      const res = await reviewsAPI.updateStatus(id, status);
      if (res.data.promo_code) {
        toast.success(`Review approved! Promo code ${res.data.promo_code} sent to customer.`);
      } else {
        toast.success(`Review ${status}!`);
      }
      fetchReviews();
    } catch (error) {
      toast.error('Failed to update status');
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
  };

  const pendingCount = reviews.filter(r => r.status === 'pending').length;
  const approvedCount = reviews.filter(r => r.status === 'approved' || !r.status).length;
  const customerCount = reviews.filter(r => r.is_customer_review).length;

  const filteredReviews = reviews.filter(r => {
    if (filter === 'pending') return r.status === 'pending';
    if (filter === 'approved') return r.status === 'approved' || !r.status;
    if (filter === 'rejected') return r.status === 'rejected';
    if (filter === 'customer') return r.is_customer_review;
    return true;
  });

  const statusBadge = (review) => {
    const s = review.status || 'approved';
    if (s === 'approved') return <Badge className="bg-green-500/20 text-green-400 border-green-500/30 text-xs">Approved</Badge>;
    if (s === 'pending') return <Badge className="bg-yellow-500/20 text-yellow-400 border-yellow-500/30 text-xs">Pending</Badge>;
    if (s === 'rejected') return <Badge className="bg-red-500/20 text-red-400 border-red-500/30 text-xs">Rejected</Badge>;
    return null;
  };

  return (
    <AdminLayout title="Reviews">
      <div className="space-y-4 lg:space-y-6" data-testid="admin-reviews">
        {/* Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <div className="bg-card border border-white/10 rounded-lg p-4">
            <p className="text-white/60 text-sm">Total</p>
            <p className="font-heading text-2xl font-bold text-white">{reviews.length}</p>
          </div>
          <div className="bg-card border border-yellow-500/30 rounded-lg p-4 cursor-pointer hover:border-yellow-500/50 transition-colors" onClick={() => setFilter(filter === 'pending' ? 'all' : 'pending')}>
            <p className="text-yellow-400 text-sm">Pending</p>
            <p className="font-heading text-2xl font-bold text-yellow-400">{pendingCount}</p>
          </div>
          <div className="bg-card border border-green-500/30 rounded-lg p-4 cursor-pointer hover:border-green-500/50 transition-colors" onClick={() => setFilter(filter === 'approved' ? 'all' : 'approved')}>
            <p className="text-green-400 text-sm">Approved</p>
            <p className="font-heading text-2xl font-bold text-green-400">{approvedCount}</p>
          </div>
          <div className="bg-card border border-amber-500/30 rounded-lg p-4 cursor-pointer hover:border-amber-500/50 transition-colors" onClick={() => setFilter(filter === 'customer' ? 'all' : 'customer')}>
            <p className="text-amber-400 text-sm">From Customers</p>
            <p className="font-heading text-2xl font-bold text-amber-400">{customerCount}</p>
          </div>
        </div>

        {/* Reward Settings */}
        <div className="bg-card border border-amber-500/20 rounded-lg p-4 lg:p-5" data-testid="review-reward-settings">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-amber-500/15 rounded-lg"><Gift className="h-5 w-5 text-amber-500" /></div>
            <div className="flex-1">
              <h3 className="font-heading font-semibold text-white text-sm">Review Reward</h3>
              <p className="text-white/50 text-xs">Customers get a discount code when their review is approved</p>
            </div>
            <Switch checked={rewardEnabled} onCheckedChange={setRewardEnabled} data-testid="reward-toggle" />
          </div>
          {rewardEnabled && (
            <div className="flex items-center gap-3">
              <Label className="text-white/60 text-sm whitespace-nowrap">Discount %</Label>
              <Input
                type="number"
                min={1}
                max={100}
                value={rewardPct}
                onChange={e => setRewardPct(Number(e.target.value))}
                className="bg-black border-white/20 w-24"
                data-testid="reward-pct-input"
              />
              <Button onClick={saveRewardSettings} disabled={savingReward} size="sm" className="bg-amber-500 hover:bg-amber-600 text-black" data-testid="save-reward-btn">
                {savingReward ? 'Saving...' : 'Save'}
              </Button>
            </div>
          )}
        </div>

        {/* Pending Alert */}
        {pendingCount > 0 && (
          <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4 flex items-center gap-3" data-testid="pending-alert">
            <Clock className="h-5 w-5 text-yellow-400 flex-shrink-0" />
            <p className="text-yellow-200 text-sm flex-1">
              <strong>{pendingCount}</strong> review{pendingCount > 1 ? 's' : ''} waiting for approval
            </p>
            <Button size="sm" className="bg-yellow-500 hover:bg-yellow-600 text-black" onClick={() => setFilter('pending')}>
              Review Now
            </Button>
          </div>
        )}

        {/* Filter tabs + Add button */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex flex-wrap gap-2">
            {['all', 'pending', 'approved', 'rejected', 'customer'].map(f => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${filter === f ? 'bg-amber-500 text-black' : 'bg-zinc-800 text-white/60 hover:text-white'}`}
                data-testid={`filter-${f}`}
              >
                {f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>
          <Button onClick={() => handleOpenDialog()} className="bg-gold-500 hover:bg-gold-600 text-black w-full sm:w-auto" data-testid="add-review-btn">
            <Plus className="h-4 w-4 mr-2" />Add Manual Review
          </Button>
        </div>

        {/* Reviews List */}
        <div className="space-y-3">
          {isLoading ? (
            <div className="text-center py-8 text-white/40">Loading...</div>
          ) : filteredReviews.length === 0 ? (
            <div className="text-center py-12 bg-card border border-white/10 rounded-lg">
              <MessageSquare className="h-12 w-12 mx-auto text-white/20 mb-4" />
              <p className="text-white/40 mb-4">No reviews match this filter</p>
            </div>
          ) : (
            filteredReviews.map((review) => (
              <div key={review.id} className={`bg-card border rounded-lg p-4 hover:border-gold-500/30 transition-all ${review.status === 'pending' ? 'border-yellow-500/30' : review.status === 'rejected' ? 'border-red-500/20' : 'border-white/10'}`} data-testid={`review-row-${review.id}`}>
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-2 flex-wrap">
                      <h3 className="font-heading font-semibold text-white">{review.reviewer_name}</h3>
                      <div className="flex items-center gap-0.5">
                        {[1, 2, 3, 4, 5].map((star) => (
                          <Star key={star} className={`h-3.5 w-3.5 ${star <= review.rating ? 'text-gold-500 fill-gold-500' : 'text-white/20'}`} />
                        ))}
                      </div>
                      {statusBadge(review)}
                      {review.is_customer_review && (
                        <Badge className="bg-amber-500/20 text-amber-400 border-amber-500/30 text-xs">Customer</Badge>
                      )}
                      <span className="text-white/40 text-xs">{formatDate(review.review_date)}</span>
                    </div>
                    <p className="text-white/70 text-sm line-clamp-2">"{review.comment}"</p>
                    {review.customer_email && (
                      <p className="text-white/30 text-xs mt-1">
                        {review.customer_email}
                        {review.reward_promo_code && <span className="ml-2 text-amber-400">Rewarded: {review.reward_promo_code}</span>}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-1 flex-shrink-0">
                    {review.status === 'pending' && (
                      <>
                        <Button variant="ghost" size="sm" onClick={() => handleStatusChange(review.id, 'approved')} className="text-green-400 hover:text-green-300 hover:bg-green-500/10 p-2" data-testid={`approve-review-${review.id}`} title="Approve">
                          <CheckCircle className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => handleStatusChange(review.id, 'rejected')} className="text-red-400 hover:text-red-300 hover:bg-red-500/10 p-2" data-testid={`reject-review-${review.id}`} title="Reject">
                          <XCircle className="h-4 w-4" />
                        </Button>
                      </>
                    )}
                    {review.status === 'rejected' && (
                      <Button variant="ghost" size="sm" onClick={() => handleStatusChange(review.id, 'approved')} className="text-green-400 hover:text-green-300 hover:bg-green-500/10 p-2" data-testid={`approve-review-${review.id}`} title="Approve">
                        <CheckCircle className="h-4 w-4" />
                      </Button>
                    )}
                    {(review.status === 'approved' || !review.status) && review.is_customer_review && (
                      <Button variant="ghost" size="sm" onClick={() => handleStatusChange(review.id, 'rejected')} className="text-red-400 hover:text-red-300 hover:bg-red-500/10 p-2" data-testid={`reject-review-${review.id}`} title="Reject">
                        <XCircle className="h-4 w-4" />
                      </Button>
                    )}
                    {!review.is_customer_review && (
                      <Button variant="ghost" size="sm" onClick={() => handleOpenDialog(review)} className="text-white/60 hover:text-gold-500 p-2" data-testid={`edit-review-${review.id}`}>
                        <Pencil className="h-4 w-4" />
                      </Button>
                    )}
                    <Button variant="ghost" size="sm" onClick={() => downloadReviewImage(review)} className="text-white/60 hover:text-amber-500 p-2" data-testid={`download-review-${review.id}`} title="Download as image">
                      <Download className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => handleDelete(review.id)} className="text-white/60 hover:text-red-500 p-2" data-testid={`delete-review-${review.id}`}>
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Add/Edit Dialog */}
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogContent className="bg-card border-white/10 text-white max-w-md sm:mx-auto">
            <DialogHeader>
              <DialogTitle className="font-heading text-xl uppercase">
                {editingReview ? 'Edit Review' : 'Add Review'}
              </DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4 lg:space-y-6">
              <div className="space-y-2">
                <Label>Reviewer Name</Label>
                <Input 
                  value={formData.reviewer_name} 
                  onChange={(e) => setFormData({ ...formData, reviewer_name: e.target.value })} 
                  className="bg-black border-white/20" 
                  placeholder="e.g. John Doe" 
                  required 
                  data-testid="review-name-input" 
                />
              </div>
              <div className="space-y-2">
                <Label>Rating</Label>
                <div className="flex items-center gap-2">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <button 
                      key={star} 
                      type="button" 
                      onClick={() => setFormData({ ...formData, rating: star })} 
                      className="p-1"
                    >
                      <Star className={`h-6 w-6 transition-colors ${star <= formData.rating ? 'text-gold-500 fill-gold-500' : 'text-white/30'}`} />
                    </button>
                  ))}
                </div>
              </div>
              <div className="space-y-2">
                <Label>Comment</Label>
                <Textarea 
                  value={formData.comment} 
                  onChange={(e) => setFormData({ ...formData, comment: e.target.value })} 
                  className="bg-black border-white/20" 
                  placeholder="Write the review..." 
                  rows={4} 
                  required 
                  data-testid="review-comment-input" 
                />
              </div>
              <div className="space-y-2">
                <Label>Review Date (optional)</Label>
                <Input 
                  type="date" 
                  value={formData.review_date} 
                  onChange={(e) => setFormData({ ...formData, review_date: e.target.value })} 
                  className="bg-black border-white/20" 
                  data-testid="review-date-input" 
                />
              </div>
              <div className="flex flex-col-reverse sm:flex-row justify-end gap-3">
                <Button type="button" variant="ghost" onClick={() => setIsDialogOpen(false)} className="w-full sm:w-auto">Cancel</Button>
                <Button type="submit" className="bg-gold-500 hover:bg-gold-600 text-black w-full sm:w-auto" data-testid="save-review-btn">
                  {editingReview ? 'Update' : 'Create'} Review
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>
    </AdminLayout>
  );
}
