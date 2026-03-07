import { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Menu, X, Search, User, Gift, Users, Smartphone } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent } from '@/components/ui/dialog';
import { CartSidebar } from '@/components/Cart';
import { CustomerAccountSidebar } from '@/components/CustomerAccount';
import CustomerAuthModal from '@/components/CustomerAuth';

const LOGO_URL = "https://customer-assets.emergentagent.com/job_8ec93a6a-4f80-4dde-b760-4bc71482fa44/artifacts/4uqt5osn_Staff.zip%20-%201.png";

export default function Navbar({ notificationBarHeight = 0 }) {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [showInstallModal, setShowInstallModal] = useState(false);
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
    
    // Listen for storage changes (for cross-tab sync and login updates)
    const handleStorageChange = () => {
      const info = localStorage.getItem('customer_info');
      if (info) {
        try {
          setCustomer(JSON.parse(info));
        } catch (e) {
          setCustomer(null);
        }
      } else {
        setCustomer(null);
      }
    };
    
    window.addEventListener('storage', handleStorageChange);
    // Also listen for custom login event
    window.addEventListener('customerLogin', handleStorageChange);
    
    return () => {
      window.removeEventListener('storage', handleStorageChange);
      window.removeEventListener('customerLogin', handleStorageChange);
    };
  }, []);

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
    { href: '/reseller-plans', label: 'Reseller', icon: Users },
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
        className={`fixed left-1/2 -translate-x-1/2 z-50 transition-all duration-500 ease-out w-[calc(100%-24px)] sm:w-auto ${
          isScrolled ? 'top-2 sm:top-3' : 'top-3 sm:top-4'
        }`}
        style={{ marginTop: notificationBarHeight }}
        data-testid="navbar"
      >
        <div 
          className={`flex items-center justify-between transition-all duration-500 ease-out rounded-full bg-black/85 backdrop-blur-xl border border-white/10 ${
            isScrolled
              ? 'px-3 sm:px-6 py-2 sm:py-2.5 gap-2 sm:gap-6 shadow-2xl shadow-black/50'
              : 'px-4 sm:px-8 py-2.5 sm:py-3.5 gap-3 sm:gap-8'
          }`}
          style={{ 
            minWidth: 'auto',
          }}
        >
          {/* Logo */}
          <Link to="/" className="flex items-center group flex-shrink-0" data-testid="nav-logo">
            <img 
              src={LOGO_URL} 
              alt="GSN" 
              className={`transition-all duration-300 group-hover:scale-105 ${isScrolled ? 'h-7 sm:h-8' : 'h-8 sm:h-9'}`} 
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
          <div className="hidden md:flex items-center gap-2">
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
              onClick={() => { setIsSearchOpen(!isSearchOpen); setIsMenuOpen(false); }} 
              className="text-white/60 hover:text-white p-1.5 h-auto rounded-full hover:bg-white/10"
            >
              <Search className="h-4 w-4" />
            </Button>
            <CartSidebar />
            {customer ? (
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={() => navigate('/account')} 
                className="text-white/60 hover:text-white p-1.5 h-auto rounded-full hover:bg-white/10"
              >
                <User className="h-4 w-4" />
              </Button>
            ) : (
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={() => setShowAuthModal(true)} 
                className="text-white/60 hover:text-white p-1.5 h-auto rounded-full hover:bg-white/10"
              >
                <User className="h-4 w-4" />
              </Button>
            )}
            <CustomerAccountSidebar />
            <button 
              onClick={() => { setIsMenuOpen(!isMenuOpen); setIsSearchOpen(false); }} 
              className="p-1.5 text-white/60 hover:text-white rounded-full hover:bg-white/10 transition-colors" 
              data-testid="mobile-menu-toggle"
            >
              {isMenuOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
            </button>
          </div>
        </div>

        {/* Mobile Dropdown Menu */}
        {(isMenuOpen || isSearchOpen) && (
          <div 
            className="md:hidden mt-2 bg-black/90 backdrop-blur-xl rounded-2xl border border-white/10 overflow-hidden shadow-2xl shadow-black/50"
            data-testid="mobile-menu"
          >
            {/* Mobile Search */}
            {isSearchOpen && (
              <div className="p-3 border-b border-white/10">
                <form onSubmit={handleSearch} className="flex items-center gap-2">
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search products..."
                    className="flex-1 bg-white/10 border border-white/10 rounded-full px-4 py-2.5 text-sm text-white placeholder:text-white/40 focus:outline-none focus:border-amber-500/50"
                    autoFocus
                  />
                  <Button type="submit" size="sm" className="bg-amber-500 hover:bg-amber-600 text-black rounded-full h-auto py-2.5 px-4">
                    <Search className="h-4 w-4" />
                  </Button>
                </form>
              </div>
            )}
            
            {/* Mobile Nav Links */}
            {isMenuOpen && (
              <div className="p-2">
                {navLinks.map((link) => (
                  <Link
                    key={link.href}
                    to={link.href}
                    onClick={() => setIsMenuOpen(false)}
                    className={`text-sm font-medium py-3 px-4 flex items-center gap-3 rounded-xl transition-colors ${
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
                
                {/* Add to Home Screen */}
                <button
                  onClick={() => { setShowInstallModal(true); setIsMenuOpen(false); }}
                  className="w-full text-sm font-medium py-3 px-4 flex items-center gap-3 rounded-xl transition-colors text-amber-400 hover:bg-white/5 mt-2 border-t border-white/10 pt-4"
                  data-testid="add-to-home-btn"
                >
                  <Smartphone className="w-4 h-4" />
                  Add to Home Screen
                </button>
              </div>
            )}
          </div>
        )}
      </nav>

      <CustomerAuthModal 
        isOpen={showAuthModal} 
        onClose={() => setShowAuthModal(false)}
        onSuccess={(customerData) => setCustomer(customerData)}
      />

      {/* Add to Home Screen Instructions Modal */}
      <Dialog open={showInstallModal} onOpenChange={setShowInstallModal}>
        <DialogContent className="w-[calc(100%-32px)] sm:max-w-[450px] p-0 bg-[#0a0a0a] border border-white/10 rounded-2xl overflow-hidden max-h-[90vh] overflow-y-auto">
          {/* Header */}
          <div className="p-6 border-b border-white/10 text-center">
            <div className="w-16 h-16 bg-amber-500/20 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <Smartphone className="w-8 h-8 text-amber-500" />
            </div>
            <h2 className="text-xl font-bold text-white">Add to Home Screen</h2>
            <p className="text-white/60 text-sm mt-2">Install GameShop Nepal for quick access</p>
          </div>

          {/* Instructions */}
          <div className="p-6 space-y-6">
            {/* Android Instructions */}
            <div className="bg-white/5 rounded-xl p-4 border border-white/10">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-green-500/20 rounded-xl flex items-center justify-center">
                  <svg className="w-5 h-5 text-green-500" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M17.6 9.48l1.84-3.18c.16-.31.04-.69-.26-.85a.637.637 0 00-.83.22l-1.88 3.24a11.463 11.463 0 00-8.94 0L5.65 5.67a.643.643 0 00-.87-.2c-.28.18-.37.54-.22.83L6.4 9.48A10.78 10.78 0 002 18h20a10.78 10.78 0 00-4.4-8.52zM7 15.25a1.25 1.25 0 110-2.5 1.25 1.25 0 010 2.5zm10 0a1.25 1.25 0 110-2.5 1.25 1.25 0 010 2.5z"/>
                  </svg>
                </div>
                <h3 className="text-white font-semibold">Android (Chrome)</h3>
              </div>
              <ol className="space-y-3 text-sm">
                <li className="flex items-start gap-3 text-white/80">
                  <span className="w-6 h-6 bg-amber-500 text-black rounded-full flex items-center justify-center flex-shrink-0 text-xs font-bold">1</span>
                  <span>Tap the <strong className="text-white">⋮ menu</strong> (3 dots) in the top right corner of Chrome</span>
                </li>
                <li className="flex items-start gap-3 text-white/80">
                  <span className="w-6 h-6 bg-amber-500 text-black rounded-full flex items-center justify-center flex-shrink-0 text-xs font-bold">2</span>
                  <span>Tap <strong className="text-white">"Add to Home screen"</strong> or <strong className="text-white">"Install app"</strong></span>
                </li>
                <li className="flex items-start gap-3 text-white/80">
                  <span className="w-6 h-6 bg-amber-500 text-black rounded-full flex items-center justify-center flex-shrink-0 text-xs font-bold">3</span>
                  <span>Tap <strong className="text-white">"Add"</strong> to confirm</span>
                </li>
              </ol>
            </div>

            {/* iOS Instructions */}
            <div className="bg-white/5 rounded-xl p-4 border border-white/10">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-blue-500/20 rounded-xl flex items-center justify-center">
                  <svg className="w-5 h-5 text-blue-500" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.81-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11z"/>
                  </svg>
                </div>
                <h3 className="text-white font-semibold">iPhone / iPad (Safari)</h3>
              </div>
              <ol className="space-y-3 text-sm">
                <li className="flex items-start gap-3 text-white/80">
                  <span className="w-6 h-6 bg-amber-500 text-black rounded-full flex items-center justify-center flex-shrink-0 text-xs font-bold">1</span>
                  <span>Open this site in <strong className="text-white">Safari</strong> browser</span>
                </li>
                <li className="flex items-start gap-3 text-white/80">
                  <span className="w-6 h-6 bg-amber-500 text-black rounded-full flex items-center justify-center flex-shrink-0 text-xs font-bold">2</span>
                  <span>Tap the <strong className="text-white">Share button</strong> (square with arrow) at the bottom</span>
                </li>
                <li className="flex items-start gap-3 text-white/80">
                  <span className="w-6 h-6 bg-amber-500 text-black rounded-full flex items-center justify-center flex-shrink-0 text-xs font-bold">3</span>
                  <span>Scroll down and tap <strong className="text-white">"Add to Home Screen"</strong></span>
                </li>
                <li className="flex items-start gap-3 text-white/80">
                  <span className="w-6 h-6 bg-amber-500 text-black rounded-full flex items-center justify-center flex-shrink-0 text-xs font-bold">4</span>
                  <span>Tap <strong className="text-white">"Add"</strong> in the top right</span>
                </li>
              </ol>
            </div>

            {/* Benefits */}
            <div className="text-center pt-2">
              <p className="text-white/40 text-xs">
                ✓ Quick access from home screen<br/>
                ✓ Faster loading<br/>
                ✓ Works like a native app
              </p>
            </div>
          </div>

          {/* Close Button */}
          <div className="p-4 border-t border-white/10">
            <Button 
              onClick={() => setShowInstallModal(false)}
              className="w-full bg-amber-500 hover:bg-amber-600 text-black font-semibold"
            >
              Got it!
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
