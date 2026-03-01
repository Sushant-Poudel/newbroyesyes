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
  const [isScrolled, setIsScrolled] = useState(false);
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

  // Dynamic navbar on scroll
  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
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
    <>
      {/* Dynamic Island Style Navbar */}
      <nav 
        className={`fixed left-1/2 -translate-x-1/2 z-50 transition-all duration-500 ease-out ${
          isScrolled 
            ? 'top-3 px-2' 
            : 'top-4 px-4'
        }`}
        style={{ marginTop: notificationBarHeight }}
        data-testid="navbar"
      >
        <div 
          className={`flex items-center justify-between transition-all duration-500 ease-out rounded-full ${
            isScrolled
              ? 'bg-black/80 backdrop-blur-xl shadow-2xl shadow-black/50 px-6 py-2.5 gap-6'
              : 'bg-black/80 backdrop-blur-xl px-8 py-3.5 gap-8'
          }`}
          style={{ 
            border: '1px solid rgba(255, 255, 255, 0.1)',
            minWidth: isScrolled ? '580px' : '650px',
          }}
        >
          {/* Logo */}
          <Link to="/" className="flex items-center group flex-shrink-0" data-testid="nav-logo">
            <img 
              src={LOGO_URL} 
              alt="GSN" 
              className={`transition-all duration-300 group-hover:scale-105 ${isScrolled ? 'h-8' : 'h-9'}`} 
            />
          </Link>

          {/* Desktop Nav Links */}
          <div className="hidden md:flex items-center gap-2">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                to={link.href}
                data-testid={`nav-link-${link.label.toLowerCase().replace(' ', '-')}`}
                className={`px-4 py-2 text-sm font-medium transition-all duration-200 flex items-center gap-2 rounded-full ${
                  link.highlight 
                    ? 'text-amber-400 hover:text-amber-300 hover:bg-amber-500/10' 
                    : isActive(link.href) 
                      ? 'text-white bg-white/10' 
                      : 'text-white/70 hover:text-white hover:bg-white/5'
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
              <form onSubmit={handleSearch} className="flex items-center gap-1">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search..."
                  className="bg-white/10 border border-white/20 rounded-full px-3 py-1 text-sm text-white placeholder:text-white/40 focus:outline-none focus:border-amber-500/50 w-36"
                  autoFocus
                  data-testid="search-input"
                />
                <Button 
                  type="button" 
                  variant="ghost" 
                  size="sm" 
                  onClick={() => { setIsSearchOpen(false); setSearchQuery(''); }} 
                  className="text-white/40 hover:text-white p-1 h-auto"
                >
                  <X className="h-4 w-4" />
                </Button>
              </form>
            ) : (
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={() => setIsSearchOpen(true)} 
                className="text-white/60 hover:text-white hover:bg-white/10 p-2 h-auto rounded-full" 
                data-testid="search-btn"
              >
                <Search className="h-4 w-4" />
              </Button>
            )}
            
            <CartSidebar />
            
            {customer ? (
              <Button 
                onClick={() => navigate('/account')} 
                className="bg-white/10 hover:bg-white/20 text-white rounded-full px-4 py-1.5 text-sm font-medium h-auto"
                data-testid="customer-account-btn"
              >
                <User className="h-3.5 w-3.5 mr-1.5" />
                Account
              </Button>
            ) : (
              <Button 
                onClick={() => setShowAuthModal(true)} 
                className="bg-white/10 hover:bg-white/20 text-white rounded-full px-4 py-1.5 text-sm font-medium h-auto"
                data-testid="customer-login-btn"
              >
                Sign In
              </Button>
            )}
            
            <CustomerAccountSidebar />
          </div>

          {/* Mobile Right Actions */}
          <div className="md:hidden flex items-center gap-0.5">
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={() => setIsSearchOpen(!isSearchOpen)} 
              className="text-white/60 hover:text-white p-1.5 h-auto rounded-full"
            >
              <Search className="h-4 w-4" />
            </Button>
            <CartSidebar />
            {customer ? (
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={() => navigate('/account')} 
                className="text-white/60 hover:text-white p-1.5 h-auto rounded-full"
              >
                <User className="h-4 w-4" />
              </Button>
            ) : (
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={() => setShowAuthModal(true)} 
                className="text-white/60 hover:text-white p-1.5 h-auto rounded-full"
              >
                <User className="h-4 w-4" />
              </Button>
            )}
            <CustomerAccountSidebar />
            <button 
              onClick={() => setIsMenuOpen(!isMenuOpen)} 
              className="p-1.5 text-white/60 hover:text-white rounded-full" 
              data-testid="mobile-menu-toggle"
            >
              {isMenuOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
            </button>
          </div>
        </div>

        {/* Mobile Menu Dropdown */}
        {isMenuOpen && (
          <div 
            className="md:hidden mt-2 bg-black/90 backdrop-blur-xl rounded-2xl border border-white/10 p-3 shadow-2xl"
            data-testid="mobile-menu"
          >
            {/* Mobile Search */}
            {isSearchOpen && (
              <form onSubmit={handleSearch} className="flex items-center gap-2 mb-3 pb-3 border-b border-white/10">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search products..."
                  className="flex-1 bg-white/10 border border-white/20 rounded-full px-3 py-2 text-sm text-white placeholder:text-white/40 focus:outline-none focus:border-amber-500/50"
                  autoFocus
                />
                <Button type="submit" size="sm" className="bg-amber-500 hover:bg-amber-600 text-black rounded-full h-auto py-2 px-3">
                  <Search className="h-4 w-4" />
                </Button>
              </form>
            )}
            
            <div className="flex flex-col space-y-1">
              {navLinks.map((link) => (
                <Link
                  key={link.href}
                  to={link.href}
                  onClick={() => setIsMenuOpen(false)}
                  className={`text-sm font-medium py-2.5 px-3 flex items-center gap-2 rounded-xl transition-colors ${
                    link.highlight 
                      ? 'text-amber-400' 
                      : isActive(link.href) 
                        ? 'text-white bg-white/10' 
                        : 'text-white/70 hover:text-white hover:bg-white/5'
                  }`}
                >
                  {link.icon && <link.icon className="w-4 h-4" />}
                  {link.label}
                </Link>
              ))}
            </div>
          </div>
        )}
      </nav>

      <CustomerAuthModal 
        isOpen={showAuthModal} 
        onClose={() => setShowAuthModal(false)}
        onSuccess={(customerData) => setCustomer(customerData)}
      />
    </>
  );
}
