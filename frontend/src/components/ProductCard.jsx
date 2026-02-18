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
  
  // Check if flash sale is active
  const isFlashSale = product.flash_sale_end && new Date(product.flash_sale_end) > new Date();
  
  // Use slug if available, otherwise fall back to ID
  const productUrl = product.slug ? `/product/${product.slug}` : `/product/${product.id}`;

  return (
    <Link
      to={productUrl}
      className="product-card group block rounded-xl overflow-hidden transition-all duration-300 hover:scale-[1.03] hover:-translate-y-1"
      data-testid={`product-card-${product.id}`}
      style={{
        border: isFlashSale ? '2px solid #ef4444' : '2px solid rgba(255, 255, 255, 0.15)',
        background: 'linear-gradient(145deg, rgba(30,30,30,1) 0%, rgba(15,15,15,1) 100%)',
        boxShadow: isFlashSale ? '0 0 15px rgba(239, 68, 68, 0.3), 0 4px 20px rgba(0,0,0,0.3)' : '0 4px 20px rgba(0,0,0,0.3)',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.border = isFlashSale ? '2px solid #ef4444' : '2px solid #f59e0b';
        e.currentTarget.style.boxShadow = isFlashSale 
          ? '0 0 20px rgba(239, 68, 68, 0.5), 0 4px 20px rgba(0,0,0,0.3)'
          : '0 0 15px rgba(245, 158, 11, 0.4), 0 4px 20px rgba(0,0,0,0.3)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.border = isFlashSale ? '2px solid #ef4444' : '2px solid rgba(255, 255, 255, 0.15)';
        e.currentTarget.style.boxShadow = isFlashSale 
          ? '0 0 15px rgba(239, 68, 68, 0.3), 0 4px 20px rgba(0,0,0,0.3)'
          : '0 4px 20px rgba(0,0,0,0.3)';
      }}
    >
      <div className="aspect-square relative overflow-hidden bg-black/50">
        <img src={product.image_url} alt={product.name} className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500" loading="lazy" />

        {/* Wishlist Button */}
        <div className="absolute top-2 left-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <WishlistButton productId={product.id} size="sm" />
        </div>
        
        {/* Flash Sale Badge */}
        {isFlashSale && (
          <FlashSaleBadge endTime={product.flash_sale_end} small={true} />
        )}

        {product.is_sold_out && (
          <div className="absolute inset-0 bg-black/70 flex items-center justify-center">
            <Badge variant="destructive" className="text-xs lg:text-sm font-heading uppercase tracking-wider">Sold Out</Badge>
          </div>
        )}

        {!product.is_sold_out && !isFlashSale && tags.length > 0 && (
          <div className="absolute top-1.5 right-1.5 lg:top-2 lg:right-2 flex flex-col gap-1">
            {tags.slice(0, 2).map(tag => (
              <Badge key={tag} className="bg-gold-500 text-black text-[10px] lg:text-xs font-semibold px-1.5 lg:px-2">{tag.toUpperCase()}</Badge>
            ))}
          </div>
        )}
      </div>

      <div className="p-3 lg:p-4 border-t border-white/10">
        <h3 className="font-heading text-sm lg:text-base font-semibold text-white truncate group-hover:text-gold-500 transition-colors">{product.name}</h3>
        <div className="mt-1.5 flex items-baseline gap-1 lg:gap-2">
          <span className={`font-bold text-base lg:text-lg ${isFlashSale ? 'text-red-500' : 'text-gold-500'}`}>Rs {lowestPrice.toLocaleString()}</span>
          {product.variations?.length > 1 && <span className="text-white/40 text-[10px] lg:text-xs">onwards</span>}
          {isFlashSale && <Zap className="w-4 h-4 text-red-500 animate-pulse" />}
        </div>
      </div>
    </Link>
  );
}
