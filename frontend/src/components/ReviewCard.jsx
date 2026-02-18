import { Star } from 'lucide-react';

export default function ReviewCard({ review }) {
  const formatDate = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
  };

  return (
    <div className="review-card bg-card/50 border border-white/10 rounded-lg p-4 lg:p-6 hover:border-gold-500/30 transition-all h-[140px] lg:h-[160px] flex flex-col" data-testid={`review-card-${review.id}`}>
      <div className="flex items-center gap-0.5 lg:gap-1 mb-2 lg:mb-3">
        {[1, 2, 3, 4, 5].map((star) => (
          <Star key={star} className={`h-3 w-3 lg:h-4 lg:w-4 ${star <= review.rating ? 'text-gold-500 fill-gold-500' : 'text-white/20'}`} />
        ))}
      </div>
      <p className="text-white/80 text-xs lg:text-sm leading-relaxed mb-3 lg:mb-4 line-clamp-2 flex-1">&ldquo;{review.comment}&rdquo;</p>
      <div className="flex items-center justify-between mt-auto">
        <span className="font-heading font-semibold text-white text-sm lg:text-base truncate max-w-[120px] lg:max-w-[150px]">{review.reviewer_name}</span>
        <span className="text-white/40 text-[10px] lg:text-xs flex-shrink-0">{formatDate(review.review_date)}</span>
      </div>
    </div>
  );
}
