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
      className="product-card group block relative rounded-3xl overflow-hidden glass-card glass-card-hover"
      data-testid={`product-card-${product.id}`}
    >
      {/* Glow effect on hover */}
      <div className={`absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none ${
        isFlashSale ? 'bg-red-500/5' : 'bg-amber-500/5'
      }`} />
      
      <div className="aspect-square relative overflow-hidden bg-black/30 rounded-t-3xl">
        <img 
          src={product.image_url} 
          alt={product.name} 
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700 ease-out" 
          loading="lazy" 
        />

        {/* Wishlist Button */}
        <div className="absolute top-3 left-3 opacity-0 group-hover:opacity-100 transition-all duration-300 translate-y-2 group-hover:translate-y-0">
          <WishlistButton productId={product.id} size="sm" />
        </div>
        
        {/* Flash Sale Badge */}
        {isFlashSale && (
          <FlashSaleBadge endTime={product.flash_sale_end} small={true} />
        )}

        {product.is_sold_out && (
          <div className="absolute inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center">
            <Badge variant="destructive" className="text-xs font-medium rounded-full px-3">Sold Out</Badge>
          </div>
        )}

        {!product.is_sold_out && !isFlashSale && tags.length > 0 && (
          <div className="absolute top-3 right-3 flex flex-col gap-1.5">
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
      </div>

      <div className="p-4 space-y-2">
        <h3 className="font-heading text-sm font-semibold text-white truncate group-hover:text-amber-500 transition-colors duration-300">
          {product.name}
        </h3>
        <div className="flex items-baseline gap-2">
          <span className={`font-bold text-lg ${isFlashSale ? 'text-red-400' : 'text-white'}`}>
            Rs {lowestPrice.toLocaleString()}
          </span>
          {product.variations?.length > 1 && (
            <span className="text-white/40 text-xs">onwards</span>
          )}
          {isFlashSale && <Zap className="w-4 h-4 text-red-400 animate-pulse" />}
        </div>
      </div>
    </Link>
  );
}
