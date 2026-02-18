import { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { 
  LayoutDashboard, Package, FolderOpen, Star, FileText, Share2, LogOut, Home, Menu, X, 
  HelpCircle, Bell, BookOpen, CreditCard, Ticket, Settings, BarChart3, Users, ShoppingCart, 
  Shield, Mail, Coins, Gift, UserPlus, Zap, ChevronDown, ChevronRight,
  Store, Megaphone, Palette, Wrench
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { authAPI } from '@/lib/api';

const LOGO_URL = "https://customer-assets.emergentagent.com/job_8ec93a6a-4f80-4dde-b760-4bc71482fa44/artifacts/4uqt5osn_Staff.zip%20-%201.png";

// Organized navigation structure with groups
const navGroups = [
  {
    id: 'main',
    label: null, // No label for main items
    items: [
      { path: '/panelgsnadminbackend', label: 'Dashboard', icon: LayoutDashboard, permission: null },
      { path: '/panelgsnadminbackend/analytics', label: 'Analytics', icon: BarChart3, permission: 'view_analytics' },
      { path: '/panelgsnadminbackend/orders', label: 'Orders', icon: ShoppingCart, permission: 'view_orders' },
    ]
  },
  {
    id: 'store',
    label: 'Store',
    icon: Store,
    items: [
      { path: '/panelgsnadminbackend/products', label: 'Products', icon: Package, permission: 'view_products' },
      { path: '/panelgsnadminbackend/categories', label: 'Categories', icon: FolderOpen, permission: 'view_categories' },
      { path: '/panelgsnadminbackend/reviews', label: 'Reviews', icon: Star, permission: 'view_reviews' },
    ]
  },
  {
    id: 'customers',
    label: 'Customers',
    icon: Users,
    items: [
      { path: '/panelgsnadminbackend/customers', label: 'All Customers', icon: Users, permission: 'view_customers' },
      { path: '/panelgsnadminbackend/staff', label: 'Staff Management', icon: Shield, permission: 'manage_admins' },
    ]
  },
  {
    id: 'marketing',
    label: 'Marketing',
    icon: Megaphone,
    items: [
      { path: '/panelgsnadminbackend/promo-codes', label: 'Promo Codes', icon: Ticket, permission: 'view_settings' },
      { path: '/panelgsnadminbackend/newsletter', label: 'Newsletter', icon: Mail, permission: 'view_settings' },
      { path: '/panelgsnadminbackend/notification-bar', label: 'Notification Bar', icon: Bell, permission: 'view_settings' },
    ]
  },
  {
    id: 'rewards',
    label: 'Rewards & Credits',
    icon: Gift,
    items: [
      { path: '/panelgsnadminbackend/credit-settings', label: 'Store Credits', icon: Coins, permission: 'view_settings' },
      { path: '/panelgsnadminbackend/daily-reward', label: 'Daily Rewards', icon: Gift, permission: 'view_settings' },
      { path: '/panelgsnadminbackend/referral', label: 'Referral Program', icon: UserPlus, permission: 'view_settings' },
      { path: '/panelgsnadminbackend/multiplier', label: 'Multiplier Events', icon: Zap, permission: 'view_settings' },
    ]
  },
  {
    id: 'content',
    label: 'Content',
    icon: Palette,
    items: [
      { path: '/panelgsnadminbackend/blog', label: 'Blog / Guides', icon: BookOpen, permission: 'view_blog' },
      { path: '/panelgsnadminbackend/pages', label: 'Pages', icon: FileText, permission: 'view_pages' },
      { path: '/panelgsnadminbackend/faqs', label: 'FAQs', icon: HelpCircle, permission: 'view_faqs' },
    ]
  },
  {
    id: 'settings',
    label: 'Settings',
    icon: Wrench,
    items: [
      { path: '/panelgsnadminbackend/pricing', label: 'Pricing', icon: Settings, permission: 'view_settings' },
      { path: '/panelgsnadminbackend/payment-methods', label: 'Payment Methods', icon: CreditCard, permission: 'view_settings' },
      { path: '/panelgsnadminbackend/social-links', label: 'Social Links', icon: Share2, permission: 'view_settings' },
    ]
  },
];

export default function AdminLayout({ children, title }) {
  const location = useLocation();
  const navigate = useNavigate();
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [user, setUser] = useState(null);
  const [expandedGroups, setExpandedGroups] = useState(['main']);
  const [userPermissions, setUserPermissions] = useState([]);
  const [isMainAdmin, setIsMainAdmin] = useState(false);

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const res = await authAPI.getMe();
        setUser(res.data);
        const permissions = res.data.permissions || [];
        setUserPermissions(permissions);
        setIsMainAdmin(res.data.is_main_admin || permissions.includes('all'));
        
        // Auto-expand group containing current page
        const currentPath = location.pathname;
        navGroups.forEach(group => {
          if (group.items.some(item => item.path === currentPath)) {
            setExpandedGroups(prev => [...new Set([...prev, group.id])]);
          }
        });
      } catch (error) {
        console.error('Error fetching user:', error);
      }
    };
    fetchUser();
  }, [location.pathname]);

  const toggleGroup = (groupId) => {
    setExpandedGroups(prev => 
      prev.includes(groupId) 
        ? prev.filter(id => id !== groupId)
        : [...prev, groupId]
    );
  };

  const hasPermission = (permission) => {
    if (!permission) return true;
    if (isMainAdmin) return true;
    return userPermissions.includes(permission);
  };

  const getVisibleItems = (items) => {
    return items.filter(item => hasPermission(item.permission));
  };

  const handleLogout = () => {
    localStorage.removeItem('admin_token');
    navigate('/panelgsnadminbackend/login');
  };

  const closeSidebar = () => setIsSidebarOpen(false);

  return (
    <div className="min-h-screen bg-black">
      {/* Mobile Header */}
      <header className="lg:hidden fixed top-0 left-0 right-0 z-50 bg-black border-b border-white/10 px-4 py-3 flex items-center justify-between">
        <Link to="/"><img src={LOGO_URL} alt="GameShop Nepal" className="h-8" /></Link>
        <button onClick={() => setIsSidebarOpen(!isSidebarOpen)} className="p-2 text-white hover:text-gold-500" data-testid="admin-mobile-menu-btn">
          {isSidebarOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
        </button>
      </header>

      {/* Mobile Overlay */}
      {isSidebarOpen && <div className="lg:hidden fixed inset-0 bg-black/80 z-40" onClick={closeSidebar} />}

      {/* Sidebar */}
      <aside className={`admin-sidebar fixed left-0 top-0 bottom-0 w-64 flex flex-col z-50 transform transition-transform duration-300 lg:translate-x-0 ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full'}`} data-testid="admin-sidebar">
        
        {/* Desktop Logo */}
        <div className="hidden lg:flex p-5 border-b border-white/10 items-center gap-3">
          <img src={LOGO_URL} alt="GameShop Nepal" className="h-9" />
          <div>
            <p className="text-white font-bold text-sm">Admin Panel</p>
            <p className="text-gray-500 text-xs">{user?.username || 'Admin'}</p>
          </div>
        </div>

        {/* Mobile Header */}
        <div className="lg:hidden p-4 border-b border-white/10 flex items-center justify-between">
          <span className="font-heading text-white uppercase tracking-wider text-sm">Menu</span>
          <button onClick={closeSidebar} className="p-1 text-white/60 hover:text-white"><X className="h-5 w-5" /></button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 py-3 overflow-y-auto">
          {navGroups.map((group) => {
            const visibleItems = getVisibleItems(group.items);
            if (visibleItems.length === 0) return null;

            const isExpanded = expandedGroups.includes(group.id);
            const hasActiveItem = visibleItems.some(item => location.pathname === item.path);
            const GroupIcon = group.icon;

            // Main items (no group header)
            if (!group.label) {
              return (
                <div key={group.id} className="px-3 mb-2">
                  {visibleItems.map((item) => {
                    const Icon = item.icon;
                    const isActive = location.pathname === item.path;
                    return (
                      <Link 
                        key={item.path} 
                        to={item.path} 
                        onClick={closeSidebar}
                        data-testid={`admin-nav-${item.label.toLowerCase().replace(/\s+/g, '-')}`}
                        className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all mb-1 ${
                          isActive 
                            ? 'bg-amber-500/10 text-amber-500 border-l-2 border-amber-500' 
                            : 'text-gray-400 hover:text-white hover:bg-white/5'
                        }`}
                      >
                        <Icon className="h-4 w-4" />
                        {item.label}
                      </Link>
                    );
                  })}
                </div>
              );
            }

            // Grouped items with collapsible header
            return (
              <div key={group.id} className="px-3 mb-1">
                <button
                  onClick={() => toggleGroup(group.id)}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-semibold uppercase tracking-wider transition-colors ${
                    hasActiveItem ? 'text-amber-500' : 'text-gray-500 hover:text-gray-300'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <GroupIcon className="h-3.5 w-3.5" />
                    {group.label}
                  </div>
                  {isExpanded ? (
                    <ChevronDown className="h-3.5 w-3.5" />
                  ) : (
                    <ChevronRight className="h-3.5 w-3.5" />
                  )}
                </button>
                
                {isExpanded && (
                  <div className="mt-1 ml-2 border-l border-white/10 pl-2">
                    {visibleItems.map((item) => {
                      const Icon = item.icon;
                      const isActive = location.pathname === item.path;
                      return (
                        <Link 
                          key={item.path} 
                          to={item.path} 
                          onClick={closeSidebar}
                          data-testid={`admin-nav-${item.label.toLowerCase().replace(/\s+/g, '-')}`}
                          className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all ${
                            isActive 
                              ? 'bg-amber-500/10 text-amber-500' 
                              : 'text-gray-400 hover:text-white hover:bg-white/5'
                          }`}
                        >
                          <Icon className="h-4 w-4" />
                          {item.label}
                        </Link>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </nav>

        {/* Footer Actions */}
        <div className="p-3 border-t border-white/10 space-y-1">
          <Link to="/" onClick={closeSidebar}>
            <Button variant="ghost" size="sm" className="w-full justify-start text-gray-400 hover:text-white hover:bg-white/5 h-9" data-testid="admin-view-site">
              <Home className="h-4 w-4 mr-2" />View Store
            </Button>
          </Link>
          <Button variant="ghost" size="sm" onClick={handleLogout} className="w-full justify-start text-red-400 hover:text-red-300 hover:bg-red-500/10 h-9" data-testid="admin-logout">
            <LogOut className="h-4 w-4 mr-2" />Logout
          </Button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="lg:ml-64 pt-14 lg:pt-0 min-h-screen">
        <div className="p-4 lg:p-6">{children}</div>
      </main>
    </div>
  );
}
