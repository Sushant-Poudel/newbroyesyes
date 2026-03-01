import { Star } from 'lucide-react';

export default function ReviewCard({ review }) {
  const formatDate = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
  };

  return (
    <div 
      className="review-card glass-card rounded-2xl p-5 lg:p-6 hover:bg-white/[0.06] transition-all duration-300 h-[150px] lg:h-[170px] flex flex-col" 
      data-testid={`review-card-${review.id}`}
    >
      <div className="flex items-center gap-1 mb-3">
        {[1, 2, 3, 4, 5].map((star) => (
          <Star 
            key={star} 
            className={`h-4 w-4 ${star <= review.rating ? 'text-[#00b67a] fill-[#00b67a]' : 'text-white/10'}`} 
          />
        ))}
      </div>
      <p className="text-white/70 text-sm leading-relaxed mb-4 line-clamp-2 flex-1">
        "{review.comment}"
      </p>
      <div className="flex items-center justify-between mt-auto pt-3 border-t border-white/5">
        <span className="font-medium text-white text-sm truncate max-w-[140px]">
          {review.reviewer_name}
        </span>
        <span className="text-white/30 text-xs flex-shrink-0">
          {formatDate(review.review_date)}
        </span>
      </div>
    </div>
  );
}
