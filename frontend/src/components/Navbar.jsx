import { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Menu, X, Search, User, Gift } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { CartSidebar } from '@/components/Cart';
import { CustomerAccountSidebar } from '@/components/CustomerAccount';
import CustomerAuthModal from '@/components/CustomerAuth';

const LOGO_URL = "https://customer-assets.emergentagent.com/job_8ec93a6a-4f80-4dde-b760-4bc71482fa44/artifacts/4uqt5osn_Staff.zip%20-%201.png";

export default function Navbar({ notificationBarHeight = 0 }) {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [customer, setCustomer] = useState(null);
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    const customerInfo = localStorage.getItem('customer_info');
    if (customerInfo) {
      try {
        setCustomer(JSON.parse(customerInfo));
      } catch (e) {}
    }
  }, []);

  const navLinks = [
    { href: '/', label: 'Home' },
    { href: '/daily-reward', label: 'Daily Rewards', icon: Gift, highlight: true },
    { href: '/about', label: 'About' },
  ];

  const isActive = (path) => location.pathname === path;

  const handleSearch = (e) => {
    e.preventDefault();
    const query = searchQuery.trim();
    if (query) {
      navigate(`/?search=${encodeURIComponent(query)}`);
      setIsSearchOpen(false);
      setSearchQuery('');
      setIsMenuOpen(false);
      setTimeout(() => {
        const productsSection = document.querySelector('[data-testid="products-section"]');
        if (productsSection) {
          productsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }, 300);
    }
  };

  return (
    <nav className="fixed left-0 right-0 z-50 bg-black/95 backdrop-blur-md border-b border-white/10" style={{ top: notificationBarHeight }} data-testid="navbar">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center" data-testid="nav-logo">
            <img src={LOGO_URL} alt="GSN" className="h-9 w-auto" />
          </Link>

          {/* Desktop Nav Links - Centered */}
          <div className="hidden md:flex items-center gap-8">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                to={link.href}
                data-testid={`nav-link-${link.label.toLowerCase().replace(' ', '-')}`}
                className={`text-sm font-medium transition-colors flex items-center gap-2 ${
                  link.highlight 
                    ? 'text-gold-500 hover:text-gold-400' 
                    : isActive(link.href) 
                      ? 'text-gold-500' 
                      : 'text-white/70 hover:text-white'
                }`}
              >
                {link.icon && <link.icon className="w-4 h-4" />}
                {link.label}
              </Link>
            ))}
          </div>

          {/* Desktop Right Actions */}
          <div className="hidden md:flex items-center gap-1">
            {isSearchOpen ? (
              <form onSubmit={handleSearch} className="flex items-center gap-2">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search..."
                  className="bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm text-white placeholder:text-white/40 focus:outline-none focus:border-gold-500/50 w-44"
                  autoFocus
                  data-testid="search-input"
                />
                <Button type="button" variant="ghost" size="sm" onClick={() => { setIsSearchOpen(false); setSearchQuery(''); }} className="text-white/40 hover:text-white p-1">
                  <X className="h-4 w-4" />
                </Button>
              </form>
            ) : (
              <Button variant="ghost" size="sm" onClick={() => setIsSearchOpen(true)} className="text-white/60 hover:text-white p-2" data-testid="search-btn">
                <Search className="h-5 w-5" />
              </Button>
            )}
            
            <CartSidebar />
            
            {customer ? (
              <Button variant="ghost" size="sm" onClick={() => navigate('/account')} className="text-white/60 hover:text-white p-2" data-testid="customer-account-btn">
                <User className="h-5 w-5" />
              </Button>
            ) : (
              <Button variant="ghost" size="sm" onClick={() => setShowAuthModal(true)} className="text-white/60 hover:text-white p-2" data-testid="customer-login-btn">
                <User className="h-5 w-5" />
              </Button>
            )}
            
            <CustomerAccountSidebar />
          </div>

          {/* Mobile Right Actions */}
          <div className="md:hidden flex items-center gap-1">
            <Button variant="ghost" size="sm" onClick={() => setIsSearchOpen(!isSearchOpen)} className="text-white/60 hover:text-white p-2">
              <Search className="h-5 w-5" />
            </Button>
            <CartSidebar />
            {customer ? (
              <Button variant="ghost" size="sm" onClick={() => navigate('/account')} className="text-white/60 hover:text-white p-2">
                <User className="h-5 w-5" />
              </Button>
            ) : (
              <Button variant="ghost" size="sm" onClick={() => setShowAuthModal(true)} className="text-white/60 hover:text-white p-2">
                <User className="h-5 w-5" />
              </Button>
            )}
            <CustomerAccountSidebar />
            <button onClick={() => setIsMenuOpen(!isMenuOpen)} className="p-2 text-white/60 hover:text-white" data-testid="mobile-menu-toggle">
              {isMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
          </div>
        </div>

        {/* Mobile Search */}
        {isSearchOpen && (
          <div className="md:hidden py-3 border-t border-white/5">
            <form onSubmit={handleSearch} className="flex items-center gap-2">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search products..."
                className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder:text-white/40 focus:outline-none focus:border-gold-500/50"
                autoFocus
              />
              <Button type="submit" size="sm" className="bg-gold-500 hover:bg-gold-600 text-black">
                <Search className="h-4 w-4" />
              </Button>
            </form>
          </div>
        )}

        {/* Mobile Menu */}
        {isMenuOpen && (
          <div className="md:hidden py-4 border-t border-white/5" data-testid="mobile-menu">
            <div className="flex flex-col space-y-3">
              {navLinks.map((link) => (
                <Link
                  key={link.href}
                  to={link.href}
                  onClick={() => setIsMenuOpen(false)}
                  className={`text-sm font-medium py-2 flex items-center gap-2 ${
                    link.highlight 
                      ? 'text-gold-500' 
                      : isActive(link.href) 
                        ? 'text-gold-500' 
                        : 'text-white/70'
                  }`}
                >
                  {link.icon && <link.icon className="w-4 h-4" />}
                  {link.label}
                </Link>
              ))}
            </div>
          </div>
        )}
      </div>

      <CustomerAuthModal 
        isOpen={showAuthModal} 
        onClose={() => setShowAuthModal(false)}
        onSuccess={(customerData) => setCustomer(customerData)}
      />
    </nav>
  );
}
