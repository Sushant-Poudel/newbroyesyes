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
    <nav 
      className={`fixed left-0 right-0 z-50 transition-all duration-300 ${
        isScrolled 
          ? 'bg-[#0a0a0a]/95 backdrop-blur-md border-b border-white/10 shadow-lg' 
          : 'bg-transparent'
      }`}
      style={{ top: notificationBarHeight }} 
      data-testid="navbar"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo Only */}
          <Link to="/" className="flex items-center group" data-testid="nav-logo">
            <img src={LOGO_URL} alt="GSN" className="h-10 w-auto transition-transform duration-300 group-hover:scale-105" />
          </Link>

          {/* Desktop Nav Links - Centered */}
          <div className="hidden md:flex items-center gap-2">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                to={link.href}
                data-testid={`nav-link-${link.label.toLowerCase().replace(' ', '-')}`}
                className={`px-4 py-2 text-sm font-medium transition-all duration-200 flex items-center gap-2 ${
                  link.highlight 
                    ? 'text-amber-500 hover:text-amber-400' 
                    : isActive(link.href) 
                      ? 'text-white' 
                      : 'text-white/60 hover:text-white'
                }`}
              >
                {link.icon && <link.icon className="w-4 h-4" />}
                {link.label}
              </Link>
            ))}
          </div>

          {/* Desktop Right Actions */}
          <div className="hidden md:flex items-center gap-2">
            {isSearchOpen ? (
              <form onSubmit={handleSearch} className="flex items-center gap-2">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search..."
                  className="bg-white/10 border border-white/20 rounded-lg px-3 py-1.5 text-sm text-white placeholder:text-white/40 focus:outline-none focus:border-amber-500/50 w-48"
                  autoFocus
                  data-testid="search-input"
                />
                <Button type="button" variant="ghost" size="sm" onClick={() => { setIsSearchOpen(false); setSearchQuery(''); }} className="text-white/40 hover:text-white p-1">
                  <X className="h-4 w-4" />
                </Button>
              </form>
            ) : (
              <Button variant="ghost" size="sm" onClick={() => setIsSearchOpen(true)} className="text-white/60 hover:text-white hover:bg-white/5 p-2" data-testid="search-btn">
                <Search className="h-5 w-5" />
              </Button>
            )}
            
            <CartSidebar />
            
            {customer ? (
              <Button 
                onClick={() => navigate('/account')} 
                className="bg-[#1a1a1a] hover:bg-[#252525] text-white border border-white/10 rounded-full px-5 py-2 text-sm font-medium"
                data-testid="customer-account-btn"
              >
                <User className="h-4 w-4 mr-2" />
                Account
              </Button>
            ) : (
              <Button 
                onClick={() => setShowAuthModal(true)} 
                className="bg-[#1a1a1a] hover:bg-[#252525] text-white border border-white/10 rounded-full px-5 py-2 text-sm font-medium"
                data-testid="customer-login-btn"
              >
                Sign In
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
          <div className="md:hidden py-3 border-t border-white/10">
            <form onSubmit={handleSearch} className="flex items-center gap-2">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search products..."
                className="flex-1 bg-white/10 border border-white/20 rounded-lg px-3 py-2 text-sm text-white placeholder:text-white/40 focus:outline-none focus:border-amber-500/50"
                autoFocus
              />
              <Button type="submit" size="sm" className="bg-amber-500 hover:bg-amber-600 text-black">
                <Search className="h-4 w-4" />
              </Button>
            </form>
          </div>
        )}

        {/* Mobile Menu */}
        {isMenuOpen && (
          <div className="md:hidden py-4 border-t border-white/10 bg-[#0a0a0a]/95 backdrop-blur-md" data-testid="mobile-menu">
            <div className="flex flex-col space-y-1">
              {navLinks.map((link) => (
                <Link
                  key={link.href}
                  to={link.href}
                  onClick={() => setIsMenuOpen(false)}
                  className={`text-sm font-medium py-3 px-2 flex items-center gap-2 rounded-lg transition-colors ${
                    link.highlight 
                      ? 'text-amber-500' 
                      : isActive(link.href) 
                        ? 'text-white bg-white/5' 
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
      </div>

      <CustomerAuthModal 
        isOpen={showAuthModal} 
        onClose={() => setShowAuthModal(false)}
        onSuccess={(customerData) => setCustomer(customerData)}
      />
    </nav>
  );
}
