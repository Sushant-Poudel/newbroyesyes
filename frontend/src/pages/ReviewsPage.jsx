import { useEffect, useState } from 'react';
import { Star, ChevronLeft, ChevronRight, MessageSquarePlus, Pencil, Send, Gift } from 'lucide-react';
import Navbar from '@/components/Navbar';
import Footer from '@/components/Footer';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { toast } from 'sonner';
import { reviewsAPI } from '@/lib/api';

function RatingBar({ label, count, total }) {
  const pct = total > 0 ? (count / total) * 100 : 0;
  return (
    <div className="flex items-center gap-3 text-sm">
      <span className="text-white/60 w-7 text-right">{label}</span>
      <Star className="h-3.5 w-3.5 text-amber-500 fill-amber-500 flex-shrink-0" />
      <div className="flex-1 h-2 bg-white/[0.06] rounded-full overflow-hidden">
        <div className="h-full bg-amber-500 rounded-full transition-all duration-500" style={{ width: `${pct}%` }} />
      </div>
      <span className="text-white/40 w-8 text-right">{count}</span>
    </div>
  );
}

export default function ReviewsPage() {
  const [data, setData] = useState({ reviews: [], total: 0, pages: 1, avg_rating: 0, distribution: {} });
  const [page, setPage] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [myReview, setMyReview] = useState(null);
  const [canReview, setCanReview] = useState(false);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [formRating, setFormRating] = useState(5);
  const [formComment, setFormComment] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isEditing, setIsEditing] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('customer_token');
    setIsLoggedIn(!!token);
    if (token) fetchMyReview();
  }, []);

  useEffect(() => { fetchReviews(); }, [page]);

  const fetchReviews = async () => {
    setIsLoading(true);
    try {
      const res = await reviewsAPI.getPublic(page);
      setData(res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchMyReview = async () => {
    try {
      const res = await reviewsAPI.getMyReview();
      setMyReview(res.data.review);
      setCanReview(res.data.can_review);
      if (res.data.review) {
        setFormRating(res.data.review.rating);
        setFormComment(res.data.review.comment);
      }
    } catch (e) {
      // Not logged in or error
    }
  };

  const handleSubmit = async () => {
    if (!formComment.trim()) { toast.error('Please write a comment'); return; }
    setIsSubmitting(true);
    try {
      if (isEditing && myReview) {
        await reviewsAPI.updateCustomerReview({ rating: formRating, comment: formComment });
        toast.success('Review updated! It will appear after admin approval.');
      } else {
        await reviewsAPI.submitCustomerReview({ rating: formRating, comment: formComment });
        toast.success('Review submitted! It will appear after admin approval.');
      }
      setShowForm(false);
      setIsEditing(false);
      fetchMyReview();
      fetchReviews();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to submit review');
    } finally {
      setIsSubmitting(false);
    }
  };

  const openEditForm = () => {
    setIsEditing(true);
    setFormRating(myReview.rating);
    setFormComment(myReview.comment);
    setShowForm(true);
  };

  const openNewForm = () => {
    setIsEditing(false);
    setFormRating(5);
    setFormComment('');
    setShowForm(true);
  };

  const formatDate = (d) => {
    if (!d) return '';
    return new Date(d).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
  };

  const { reviews, total, pages, avg_rating, distribution } = data;

  return (
    <div className="min-h-screen bg-black">
      <Navbar />

      <div className="pt-24 lg:pt-28 pb-16">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">

          {/* Header */}
          <div className="text-center mb-10" data-testid="reviews-page-header">
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-white tracking-tight">Customer Reviews</h1>
            <p className="text-white/50 mt-3 text-sm sm:text-base">Hear what our customers have to say</p>
          </div>

          {/* Stats Card */}
          <div className="bg-zinc-900/60 border border-white/[0.06] rounded-2xl p-6 sm:p-8 mb-8" data-testid="reviews-stats">
            <div className="flex flex-col sm:flex-row gap-8">
              {/* Average Rating */}
              <div className="flex flex-col items-center justify-center sm:min-w-[160px]">
                <span className="text-5xl font-extrabold text-white tracking-tight">{avg_rating || '0'}</span>
                <div className="flex items-center gap-0.5 mt-2">
                  {[1, 2, 3, 4, 5].map(s => (
                    <Star key={s} className={`h-4 w-4 ${s <= Math.round(avg_rating) ? 'text-amber-500 fill-amber-500' : 'text-white/10'}`} />
                  ))}
                </div>
                <span className="text-white/40 text-sm mt-1.5">{total} review{total !== 1 ? 's' : ''}</span>
              </div>

              {/* Distribution */}
              <div className="flex-1 space-y-2">
                {[5, 4, 3, 2, 1].map(r => (
                  <RatingBar key={r} label={r} count={distribution[String(r)] || 0} total={total} />
                ))}
              </div>
            </div>
          </div>

          {/* Reward Incentive */}
          <div className="flex items-center justify-center gap-3 mb-6 bg-amber-500/5 border border-amber-500/15 rounded-xl px-5 py-3" data-testid="review-reward-banner">
            <Gift className="h-5 w-5 text-amber-500 flex-shrink-0" />
            <p className="text-white/70 text-sm">Leave a review and get a <span className="text-amber-500 font-semibold">discount code</span> for your next purchase!</p>
          </div>

          {/* Action Button */}
          <div className="flex justify-center mb-8">
            {isLoggedIn ? (
              canReview ? (
                myReview ? (
                  <div className="flex flex-col items-center gap-2">
                    <div className="bg-zinc-900/60 border border-amber-500/20 rounded-xl p-4 text-center">
                      <p className="text-white/60 text-sm mb-1">Your review {myReview.status === 'pending' ? '(pending approval)' : myReview.status === 'approved' ? '(published)' : `(${myReview.status})`}</p>
                      <div className="flex items-center justify-center gap-0.5 mb-1">
                        {[1,2,3,4,5].map(s => <Star key={s} className={`h-3.5 w-3.5 ${s <= myReview.rating ? 'text-amber-500 fill-amber-500' : 'text-white/10'}`} />)}
                      </div>
                      <p className="text-white/70 text-sm">"{myReview.comment}"</p>
                    </div>
                    <Button onClick={openEditForm} variant="outline" size="sm" className="border-white/15 text-white/70 hover:bg-white/5" data-testid="edit-my-review-btn">
                      <Pencil className="h-3.5 w-3.5 mr-1.5" />Edit My Review
                    </Button>
                  </div>
                ) : (
                  <Button onClick={openNewForm} className="bg-amber-500 hover:bg-amber-600 text-black font-semibold px-6" data-testid="write-review-btn">
                    <MessageSquarePlus className="h-4 w-4 mr-2" />Write a Review
                  </Button>
                )
              ) : (
                <p className="text-white/40 text-sm bg-zinc-900/40 border border-white/[0.06] rounded-xl px-5 py-3" data-testid="no-order-msg">
                  Complete an order to leave a review
                </p>
              )
            ) : (
              <p className="text-white/40 text-sm bg-zinc-900/40 border border-white/[0.06] rounded-xl px-5 py-3" data-testid="login-prompt">
                Sign in to leave a review
              </p>
            )}
          </div>

          {/* Reviews List */}
          <div className="space-y-4" data-testid="reviews-list">
            {isLoading ? (
              <div className="space-y-4">
                {[1,2,3].map(i => <div key={i} className="h-32 bg-zinc-900/50 rounded-xl animate-pulse" />)}
              </div>
            ) : reviews.length > 0 ? (
              reviews.map(review => (
                <div key={review.id} className="bg-zinc-900/60 border border-white/[0.06] rounded-xl p-5 hover:border-white/10 transition-colors" data-testid={`public-review-${review.id}`}>
                  <div className="flex items-center gap-0.5 mb-2.5">
                    {[1,2,3,4,5].map(s => (
                      <Star key={s} className={`h-4 w-4 ${s <= review.rating ? 'text-amber-500 fill-amber-500' : 'text-white/10'}`} />
                    ))}
                  </div>
                  <p className="text-white/70 text-sm leading-relaxed mb-3">"{review.comment}"</p>
                  <div className="flex items-center justify-between border-t border-white/5 pt-3">
                    <div className="flex items-center gap-2">
                      <div className="w-7 h-7 rounded-full bg-amber-500/15 flex items-center justify-center">
                        <span className="text-amber-500 text-xs font-bold">{review.reviewer_name?.[0]?.toUpperCase() || '?'}</span>
                      </div>
                      <span className="text-white font-medium text-sm">{review.reviewer_name}</span>
                      {review.is_customer_review && (
                        <span className="text-xs bg-amber-500/10 text-amber-500 px-2 py-0.5 rounded-full">Verified Buyer</span>
                      )}
                    </div>
                    <span className="text-white/25 text-xs">{formatDate(review.review_date)}</span>
                  </div>
                </div>
              ))
            ) : (
              <div className="flex flex-col items-center justify-center py-16" data-testid="empty-state-reviews">
                <div className="relative mb-6">
                  <div className="absolute inset-0 bg-amber-500/10 rounded-full blur-xl scale-150" />
                  <div className="relative p-5 rounded-full bg-gradient-to-br from-white/[0.06] to-white/[0.02] border border-white/[0.08]">
                    <Star className="h-8 w-8 text-white/25" strokeWidth={1.5} />
                  </div>
                </div>
                <h3 className="font-heading text-lg font-semibold text-white/80 mb-2">No reviews yet</h3>
                <p className="text-white/40 text-sm">Be the first to share your experience!</p>
              </div>
            )}
          </div>

          {/* Pagination */}
          {pages > 1 && (
            <div className="flex items-center justify-center gap-3 mt-8" data-testid="reviews-pagination">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage(p => p - 1)}
                className="border-white/15 text-white/70 hover:bg-white/5 disabled:opacity-30"
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <span className="text-white/50 text-sm">Page {page} of {pages}</span>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= pages}
                onClick={() => setPage(p => p + 1)}
                className="border-white/15 text-white/70 hover:bg-white/5 disabled:opacity-30"
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          )}
        </div>
      </div>

      <Footer />

      {/* Review Form Dialog */}
      <Dialog open={showForm} onOpenChange={setShowForm}>
        <DialogContent className="w-[calc(100%-32px)] sm:max-w-md bg-[#0a0a0a] border border-white/10 rounded-2xl text-white" data-testid="review-form-dialog">
          <DialogHeader>
            <DialogTitle className="text-xl font-bold">{isEditing ? 'Edit Your Review' : 'Write a Review'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-5 pt-2">
            <div>
              <label className="text-white/60 text-sm mb-2 block">Your Rating</label>
              <div className="flex items-center gap-1.5">
                {[1,2,3,4,5].map(s => (
                  <button key={s} type="button" onClick={() => setFormRating(s)} className="p-1 transition-transform hover:scale-110" data-testid={`rating-star-${s}`}>
                    <Star className={`h-7 w-7 transition-colors ${s <= formRating ? 'text-amber-500 fill-amber-500' : 'text-white/20'}`} />
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="text-white/60 text-sm mb-2 block">Your Experience</label>
              <Textarea
                value={formComment}
                onChange={e => setFormComment(e.target.value)}
                placeholder="Tell us about your experience..."
                className="bg-white/5 border-white/10 text-white placeholder:text-white/30 min-h-[120px] resize-none"
                data-testid="review-comment-textarea"
              />
            </div>
            <div className="flex gap-3 pt-1">
              <Button variant="ghost" onClick={() => setShowForm(false)} className="flex-1 text-white/60">Cancel</Button>
              <Button
                onClick={handleSubmit}
                disabled={isSubmitting || !formComment.trim()}
                className="flex-1 bg-amber-500 hover:bg-amber-600 text-black font-semibold"
                data-testid="submit-review-btn"
              >
                <Send className="h-4 w-4 mr-2" />
                {isSubmitting ? 'Submitting...' : isEditing ? 'Update Review' : 'Submit Review'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
