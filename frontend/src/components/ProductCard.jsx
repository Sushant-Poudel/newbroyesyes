import { Link } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { WishlistButton } from '@/components/Wishlist';
import { FlashSaleBadge } from '@/components/FlashSale';
import { Zap } from 'lucide-react';

export default function ProductCard({ product }) {
  const lowestPrice = product.variations?.length > 0
    ? Math.min(...product.variations.map(v => v.price))
    : 0;

  const tags = product.tags || [];
  const isFlashSale = product.flash_sale_end && new Date(product.flash_sale_end) > new Date();
  const productUrl = product.slug ? `/product/${product.slug}` : `/product/${product.id}`;

  return (
    <Link
      to={productUrl}
      className="group block relative rounded-xl overflow-hidden bg-zinc-900/60 border border-white/[0.06] hover:border-amber-500/20 transition-all duration-300"
      data-testid={`product-card-${product.id}`}
    >
      <div className="aspect-square relative overflow-hidden bg-black/30">
        <img 
          src={product.image_url} 
          alt={product.name} 
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500 ease-out" 
          loading="lazy" 
        />

        <div className="absolute top-2.5 left-2.5 opacity-0 group-hover:opacity-100 transition-all duration-300">
          <WishlistButton productId={product.id} size="sm" />
        </div>
        
        {isFlashSale && (
          <FlashSaleBadge endTime={product.flash_sale_end} small={true} />
        )}

        {product.is_sold_out && (
          <div className="absolute inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center">
            <Badge variant="destructive" className="text-xs font-medium rounded-full px-3">Sold Out</Badge>
          </div>
        )}

        {!product.is_sold_out && !isFlashSale && tags.length > 0 && (
          <div className="absolute top-2.5 right-2.5 flex flex-col gap-1">
            {tags.slice(0, 2).map(tag => (
              <Badge 
                key={tag} 
                className="bg-white text-black text-[10px] font-semibold px-2 py-0.5 rounded-full shadow-lg"
              >
                {tag}
              </Badge>
            ))}
          </div>
        )}

        {/* Bottom gradient for text readability */}
        <div className="absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-black/70 to-transparent pointer-events-none" />
      </div>

      <div className="p-3 sm:p-3.5">
        <h3 className="text-[13px] sm:text-sm font-semibold text-white truncate group-hover:text-amber-400 transition-colors duration-200">
          {product.name}
        </h3>
        <div className="flex items-baseline gap-1.5 mt-1">
          <span className={`font-bold text-base sm:text-lg ${isFlashSale ? 'text-red-400' : 'text-white'}`}>
            Rs {lowestPrice.toLocaleString()}
          </span>
          {product.variations?.length > 1 && (
            <span className="text-white/35 text-xs">onwards</span>
          )}
          {isFlashSale && <Zap className="w-3.5 h-3.5 text-red-400 animate-pulse" />}
        </div>
      </div>
    </Link>
  );
}
