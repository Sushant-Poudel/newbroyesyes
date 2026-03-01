import { useEffect, useState, useRef } from 'react';
import { Link } from 'react-router-dom';
import { Star, ExternalLink, Search, X, Shield, Clock, Headphones, Lock, Zap, ChevronRight } from 'lucide-react';
import Navbar from '@/components/Navbar';
import Footer from '@/components/Footer';
import ProductCard from '@/components/ProductCard';
import ReviewCard from '@/components/ReviewCard';
import { Button } from '@/components/ui/button';
import { productsAPI, categoriesAPI, reviewsAPI, notificationBarAPI, blogAPI, paymentMethodsAPI } from '@/lib/api';

const TRUSTPILOT_URL = "https://www.trustpilot.com/review/gameshopnepal.com";

const TRUST_FEATURES = [
  { icon: Shield, title: 'Secure Payments', desc: '100% safe & encrypted' },
  { icon: Lock, title: 'Data Privacy', desc: 'Your info is protected' },
  { icon: Zap, title: 'Fast Delivery', desc: 'Within minutes' },
  { icon: Headphones, title: '24/7 Support', desc: 'Always here to help' },
];

export default function HomePage() {
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [reviews, setReviews] = useState([]);
  const [blogPosts, setBlogPosts] = useState([]);
  const [paymentMethods, setPaymentMethods] = useState([]);
  const [notificationBar, setNotificationBar] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const productsSectionRef = useRef(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [productsRes, categoriesRes, reviewsRes, notifRes, blogRes, paymentRes] = await Promise.all([
          productsAPI.getAll(),
          categoriesAPI.getAll(),
          reviewsAPI.getAll(),
          notificationBarAPI.get().catch(() => ({ data: null })),
          blogAPI.getAll().catch(() => ({ data: [] })),
          paymentMethodsAPI.getAll().catch(() => ({ data: [] })),
        ]);
        setProducts(productsRes.data);
        setCategories(categoriesRes.data);
        // Limit reviews to latest 20
        const sortedReviews = reviewsRes.data
          .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
          .slice(0, 20);
        setReviews(sortedReviews);
        setNotificationBar(notifRes.data);
        setBlogPosts(blogRes.data.slice(0, 3));
        setPaymentMethods(paymentRes.data);
      } catch (error) {
        console.error('Error:', error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchData();

    const params = new URLSearchParams(window.location.search);
    const search = params.get('search');
    if (search) setSearchQuery(search);
  }, []);

  const filteredProducts = products.filter(product => {
    const matchesCategory = !selectedCategory || product.category_id === selectedCategory;
    const matchesSearch = !searchQuery || product.name.toLowerCase().includes(searchQuery.toLowerCase()) || product.description?.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  const hotDeals = products.filter(p => p.tags?.includes('Hot') || p.tags?.includes('Sale')).slice(0, 5);
  const bestSellers = products.filter(p => p.tags?.includes('Popular') || p.tags?.includes('Best Seller')).slice(0, 5);
  const newArrivals = products.filter(p => p.tags?.includes('New')).slice(0, 5);

  const clearSearch = () => {
    setSearchQuery('');
    window.history.replaceState({}, '', '/');
  };

  const hasNotification = notificationBar && notificationBar.is_active && notificationBar.text;

  return (
    <div className="min-h-screen bg-black bg-mesh">
      {hasNotification && (
        <div className="fixed top-0 left-0 right-0 z-[60] py-2.5 px-4 text-center text-sm font-medium backdrop-blur-xl" style={{ backgroundColor: notificationBar.bg_color + 'dd', color: notificationBar.text_color }}>
          {notificationBar.link ? <a href={notificationBar.link} className="hover:underline">{notificationBar.text}</a> : notificationBar.text}
        </div>
      )}

      <Navbar notificationBarHeight={hasNotification ? 40 : 0} />

      {/* Hero Section - Apple Style */}
      <section className={`relative ${hasNotification ? 'pt-32' : 'pt-28'} pb-16`}>
        {/* Background Glow */}
        <div className="absolute inset-0 bg-hero-glow pointer-events-none" />
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[400px] bg-[#2997FF]/10 rounded-full blur-[120px] pointer-events-none" />
        
        <div className="relative max-w-5xl mx-auto px-6 text-center">
          <p className="text-[#2997FF] text-sm font-medium tracking-widest uppercase mb-4 animate-fade-in">Premium Digital Products</p>
          <h1 className="font-heading text-5xl md:text-7xl lg:text-8xl font-extrabold text-white tracking-tight leading-[0.95] mb-6 animate-slide-up">
            Your Digital<br />
            <span className="text-gradient-blue">Lifestyle.</span>
          </h1>
          <p className="text-white/60 text-lg md:text-xl max-w-2xl mx-auto mb-10 animate-slide-up stagger-2">
            Netflix, Spotify, YouTube Premium and more. Instant delivery, unbeatable prices.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 animate-slide-up stagger-3">
            <Button 
              onClick={() => productsSectionRef.current?.scrollIntoView({ behavior: 'smooth' })}
              className="btn-primary px-8 py-6 text-base"
            >
              Explore Products
            </Button>
            <a href={TRUSTPILOT_URL} target="_blank" rel="noopener noreferrer">
              <Button variant="ghost" className="text-white/70 hover:text-white gap-2">
                <div className="flex">{[1,2,3,4,5].map((i) => <Star key={i} className="w-4 h-4 text-[#00b67a] fill-[#00b67a]" />)}</div>
                Excellent on Trustpilot
              </Button>
            </a>
          </div>
        </div>
      </section>

      {/* Trust Features */}
      <section className="py-12 border-y border-white/5">
        <div className="max-w-6xl mx-auto px-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {TRUST_FEATURES.map((feature, i) => (
              <div key={feature.title} className={`text-center animate-fade-in stagger-${i+1}`}>
                <div className="w-12 h-12 mx-auto mb-3 rounded-2xl glass flex items-center justify-center">
                  <feature.icon className="w-5 h-5 text-[#2997FF]" />
                </div>
                <h3 className="text-white font-medium text-sm mb-1">{feature.title}</h3>
                <p className="text-white/40 text-xs">{feature.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Reviews Marquee */}
      <section className="py-16" data-testid="reviews-section">
        <div className="max-w-7xl mx-auto px-6 mb-8">
          <h2 className="font-heading text-3xl md:text-4xl font-bold text-white tracking-tight text-center mb-2">What Our Customers Say</h2>
          <p className="text-white/40 text-center">Trusted by thousands of happy customers</p>
        </div>

        {isLoading ? (
          <div className="flex gap-6 px-6">{[1, 2, 3, 4].map((i) => <div key={i} className="h-40 w-80 glass-card rounded-3xl flex-shrink-0 animate-pulse"></div>)}</div>
        ) : reviews.length > 0 ? (
          <div className="reviews-marquee-container">
            <div className="reviews-marquee">
              {reviews.map((review) => <div key={review.id} className="review-slide"><ReviewCard review={review} /></div>)}
              {reviews.map((review) => <div key={`dup-${review.id}`} className="review-slide"><ReviewCard review={review} /></div>)}
            </div>
          </div>
        ) : <div className="text-center py-6 text-white/40">No reviews yet</div>}
      </section>

      {hotDeals.length > 0 && (
        <section className="py-8 lg:py-10">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-heading text-xl sm:text-2xl font-bold text-white uppercase tracking-tight flex items-center gap-2">Hot Deals</h2>
              <Link to="/" className="text-gold-500 text-sm hover:underline flex items-center gap-1">View All <ChevronRight className="h-4 w-4" /></Link>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">{hotDeals.map((product) => <ProductCard key={product.id} product={product} />)}</div>
          </div>
        </section>
      )}

      {bestSellers.length > 0 && (
        <section className="py-8 lg:py-10 bg-card/30">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-heading text-xl sm:text-2xl font-bold text-white uppercase tracking-tight flex items-center gap-2">Best Sellers</h2>
              <Link to="/" className="text-gold-500 text-sm hover:underline flex items-center gap-1">View All <ChevronRight className="h-4 w-4" /></Link>
            </div>
            <div className="flex gap-3 overflow-x-auto pb-4 scrollbar-hide snap-x snap-mandatory">
              {bestSellers.map((product) => <div key={product.id} className="flex-shrink-0 w-[160px] sm:w-[180px] lg:w-[200px] snap-start"><ProductCard product={product} /></div>)}
            </div>
          </div>
        </section>
      )}

      {newArrivals.length > 0 && (
        <section className="py-8 lg:py-10">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-heading text-xl sm:text-2xl font-bold text-white uppercase tracking-tight flex items-center gap-2">New Arrivals</h2>
              <Link to="/" className="text-gold-500 text-sm hover:underline flex items-center gap-1">View All <ChevronRight className="h-4 w-4" /></Link>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">{newArrivals.map((product) => <ProductCard key={product.id} product={product} />)}</div>
          </div>
        </section>
      )}

      <section ref={productsSectionRef} className="py-8 lg:py-12" data-testid="products-section">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-6 lg:mb-8">
            <h2 className="font-heading text-3xl sm:text-4xl md:text-5xl font-bold text-white uppercase tracking-tight mb-2 lg:mb-3 animate-fade-in">All <span className="text-gold-500">Products</span></h2>
            <p className="text-white/60 max-w-2xl mx-auto text-sm lg:text-base">Browse our collection of premium digital products.</p>
          </div>

          {searchQuery && (
            <div className="flex items-center justify-center gap-2 mb-4 lg:mb-6 animate-scale-in">
              <div className="flex items-center gap-2 bg-gold-500/10 border border-gold-500/30 rounded-full px-4 py-2">
                <Search className="h-4 w-4 text-gold-500" />
                <span className="text-white text-sm">Results for "<span className="text-gold-500">{searchQuery}</span>"</span>
                <button onClick={clearSearch} className="ml-1 p-1 hover:bg-white/10 rounded-full transition-colors"><X className="h-4 w-4 text-white/60 hover:text-white" /></button>
              </div>
            </div>
          )}

          <div className="flex flex-wrap items-center justify-center gap-2 mb-6 lg:mb-8">
            <button onClick={() => setSelectedCategory(null)} className={`category-pill px-3 lg:px-4 py-1.5 rounded-full border text-xs lg:text-sm font-heading uppercase tracking-wider transition-all duration-300 hover:scale-105 ${selectedCategory === null ? 'bg-gold-500/20 border-gold-500 text-gold-500' : 'border-white/20 text-white/60 hover:border-gold-500/50 hover:text-gold-500'}`}>All</button>
            {categories.map((cat) => (
              <button key={cat.id} onClick={() => setSelectedCategory(cat.id)} className={`category-pill px-3 lg:px-4 py-1.5 rounded-full border text-xs lg:text-sm font-heading uppercase tracking-wider transition-all duration-300 hover:scale-105 ${selectedCategory === cat.id ? 'bg-gold-500/20 border-gold-500 text-gold-500' : 'border-white/20 text-white/60 hover:border-gold-500/50 hover:text-gold-500'}`}>{cat.name}</button>
            ))}
          </div>

          {isLoading ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3 lg:gap-5">{[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((i) => <div key={i} className="aspect-square skeleton rounded-lg"></div>)}</div>
          ) : filteredProducts.length > 0 ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3 lg:gap-5">
              {filteredProducts.map((product, index) => <div key={product.id} className="animate-fade-in" style={{ animationDelay: `${index * 30}ms` }}><ProductCard product={product} /></div>)}
            </div>
          ) : <div className="text-center py-10"><p className="text-white/40 text-lg">No products found.</p></div>}
        </div>
      </section>

      {paymentMethods.length > 0 && (
        <section className="py-8 lg:py-10 bg-gradient-to-r from-gold-500/10 via-gold-500/5 to-gold-500/10">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <h2 className="font-heading text-xl sm:text-2xl font-bold text-white uppercase tracking-tight mb-4 text-center">Payment Options</h2>
            <div className="flex flex-wrap items-center justify-center gap-4 lg:gap-6">
              {paymentMethods.map((method) => (
                <div key={method.id} className="bg-card/50 border border-white/10 rounded-lg px-4 py-3 flex items-center gap-3 hover:border-gold-500/50 transition-colors">
                  <img src={method.image_url} alt={method.name} className="h-8 w-auto object-contain" onError={(e) => e.target.style.display = 'none'} />
                  <span className="text-white font-medium text-sm">{method.name}</span>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      <section className="py-8 lg:py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="font-heading text-2xl sm:text-3xl font-bold text-white uppercase tracking-tight mb-6 text-center">Trust & <span className="text-gold-500">Safety</span></h2>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {TRUST_FEATURES.map((feature, i) => {
              const Icon = feature.icon;
              return (
                <div key={i} className="bg-card border border-white/10 rounded-lg p-4 text-center hover:border-gold-500/50 transition-all duration-300">
                  <div className="w-12 h-12 bg-gold-500/20 rounded-full flex items-center justify-center mx-auto mb-3"><Icon className="h-6 w-6 text-gold-500" /></div>
                  <h3 className="font-heading font-semibold text-white text-sm">{feature.title}</h3>
                  <p className="text-white/60 text-xs mt-1">{feature.desc}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {blogPosts.length > 0 && (
        <section className="py-8 lg:py-12 bg-card/30">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between mb-6">
              <h2 className="font-heading text-2xl sm:text-3xl font-bold text-white uppercase tracking-tight">Guides & <span className="text-gold-500">Tips</span></h2>
              <Link to="/blog" className="text-gold-500 text-sm hover:underline flex items-center gap-1">View All <ChevronRight className="h-4 w-4" /></Link>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {blogPosts.map((post) => (
                <Link key={post.id} to={`/blog/${post.slug}`} className="bg-card border border-white/10 rounded-lg overflow-hidden hover:border-gold-500/50 transition-all duration-300 group">
                  {post.image_url && <img src={post.image_url} alt={post.title} className="w-full h-32 object-cover" />}
                  <div className="p-4">
                    <h3 className="font-heading font-semibold text-white group-hover:text-gold-500 transition-colors line-clamp-2">{post.title}</h3>
                    <p className="text-white/60 text-sm mt-2 line-clamp-2">{post.excerpt}</p>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </section>
      )}

      <Footer />
    </div>
  );
}
