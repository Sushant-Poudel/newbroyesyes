import { useEffect, useState } from 'react';
import { Package, FolderOpen, Star, Share2, Webhook, CheckCircle, XCircle, ExternalLink } from 'lucide-react';
import { Link } from 'react-router-dom';
import AdminLayout from '@/components/AdminLayout';
import { productsAPI, categoriesAPI, reviewsAPI, socialLinksAPI } from '@/lib/api';
import axios from 'axios';

const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function AdminDashboard() {
  const [stats, setStats] = useState({ products: 0, categories: 0, reviews: 0, socialLinks: 0 });
  const [webhooks, setWebhooks] = useState({ global: null, products: [] });
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const token = localStorage.getItem('admin_token');
        const headers = { Authorization: `Bearer ${token}` };
        
        const [productsRes, categoriesRes, reviewsRes, linksRes, webhookSettings, webhookProducts] = await Promise.all([
          productsAPI.getAll(null, false),
          categoriesAPI.getAll(),
          reviewsAPI.getAll(),
          socialLinksAPI.getAll(),
          axios.get(`${API_URL}/webhooks/settings`, { headers }).catch(() => ({ data: {} })),
          axios.get(`${API_URL}/webhooks/products`, { headers }).catch(() => ({ data: [] }))
        ]);
        
        setStats({ 
          products: productsRes.data.length, 
          categories: categoriesRes.data.length, 
          reviews: reviewsRes.data.length, 
          socialLinks: Array.isArray(linksRes.data) ? linksRes.data.length : 0 
        });
        
        setWebhooks({
          global: webhookSettings.data,
          products: webhookProducts.data || []
        });
      } catch (error) {
        console.error('Error fetching data:', error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchData();
  }, []);

  const statCards = [
    { label: 'Categories', value: stats.categories, icon: FolderOpen, color: 'bg-purple-500/10 text-purple-500', link: '/panelgsnadminbackend/categories' },
    { label: 'Products', value: stats.products, icon: Package, color: 'bg-blue-500/10 text-blue-500', link: '/panelgsnadminbackend/products' },
    { label: 'Reviews', value: stats.reviews, icon: Star, color: 'bg-gold-500/10 text-gold-500', link: '/panelgsnadminbackend/reviews' },
    { label: 'Social Links', value: stats.socialLinks, icon: Share2, color: 'bg-green-500/10 text-green-500', link: '/panelgsnadminbackend/social-links' },
  ];

  return (
    <AdminLayout title="Dashboard">
      <div className="space-y-6" data-testid="admin-dashboard">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 lg:gap-6">
          {statCards.map((stat) => {
            const Icon = stat.icon;
            return (
              <Link key={stat.label} to={stat.link} className="bg-card border border-white/10 rounded-lg p-4 lg:p-6 hover:border-gold-500/30 transition-all" data-testid={`stat-card-${stat.label.toLowerCase()}`}>
                <div className="flex items-center justify-between mb-3 lg:mb-4"><div className={`p-2 lg:p-3 rounded-lg ${stat.color}`}><Icon className="h-4 w-4 lg:h-6 lg:w-6" /></div></div>
                <h3 className="text-white/60 text-xs lg:text-sm mb-1">{stat.label}</h3>
                <p className="font-heading text-2xl lg:text-3xl font-bold text-white">{isLoading ? '-' : stat.value}</p>
              </Link>
            );
          })}
        </div>

        <div className="bg-card border border-white/10 rounded-lg p-4 lg:p-6">
          <h2 className="font-heading text-lg lg:text-xl font-semibold text-white uppercase mb-4">Quick Actions</h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 lg:gap-4">
            <Link to="/panelgsnadminbackend/categories" className="flex items-center gap-3 p-3 lg:p-4 bg-black rounded-lg border border-white/10 hover:border-gold-500/50 transition-all" data-testid="quick-action-categories"><FolderOpen className="h-5 w-5 text-gold-500 flex-shrink-0" /><span className="text-white text-sm lg:text-base">Manage Categories</span></Link>
            <Link to="/panelgsnadminbackend/products" className="flex items-center gap-3 p-3 lg:p-4 bg-black rounded-lg border border-white/10 hover:border-gold-500/50 transition-all" data-testid="quick-action-products"><Package className="h-5 w-5 text-gold-500 flex-shrink-0" /><span className="text-white text-sm lg:text-base">Manage Products</span></Link>
            <Link to="/panelgsnadminbackend/reviews" className="flex items-center gap-3 p-3 lg:p-4 bg-black rounded-lg border border-white/10 hover:border-gold-500/50 transition-all" data-testid="quick-action-reviews"><Star className="h-5 w-5 text-gold-500 flex-shrink-0" /><span className="text-white text-sm lg:text-base">Manage Reviews</span></Link>
          </div>
        </div>

        <div className="bg-gradient-to-r from-gold-500/10 to-transparent border border-gold-500/20 rounded-lg p-4 lg:p-6">
          <h2 className="font-heading text-lg lg:text-xl font-semibold text-white mb-2">Welcome to GameShop Nepal Admin</h2>
          <p className="text-white/60 text-sm lg:text-base">Manage your products, reviews, pages, and social media links from this dashboard.</p>
        </div>

        {/* Webhooks Section */}
        <div className="bg-card border border-white/10 rounded-lg p-4 lg:p-6">
          <div className="flex items-center gap-3 mb-4">
            <Webhook className="h-5 w-5 text-amber-500" />
            <h2 className="font-heading text-lg lg:text-xl font-semibold text-white">Connected Webhooks</h2>
          </div>
          
          {/* Global Order Webhook */}
          <div className="mb-4 p-4 bg-black rounded-lg border border-white/10">
            <div className="flex items-center justify-between mb-2">
              <span className="text-white font-medium">Global Order Webhook</span>
              {webhooks.global?.discord_order_webhook_active ? (
                <span className="flex items-center gap-1 text-green-400 text-sm">
                  <CheckCircle className="h-4 w-4" /> Active
                </span>
              ) : (
                <span className="flex items-center gap-1 text-red-400 text-sm">
                  <XCircle className="h-4 w-4" /> Not Configured
                </span>
              )}
            </div>
            <p className="text-white/50 text-xs">Receives notifications for all confirmed orders</p>
            {webhooks.global?.discord_order_webhook && (
              <code className="block mt-2 text-xs text-amber-400 bg-amber-500/10 p-2 rounded truncate">
                {webhooks.global.discord_order_webhook.substring(0, 60)}...
              </code>
            )}
          </div>

          {/* Product-Specific Webhooks */}
          <div className="space-y-2">
            <h3 className="text-white/60 text-sm mb-2">Product-Specific Webhooks ({webhooks.products.length})</h3>
            {webhooks.products.length === 0 ? (
              <p className="text-white/40 text-sm">No products have custom webhooks configured.</p>
            ) : (
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {webhooks.products.map((product) => (
                  <div key={product.id} className="flex items-center justify-between p-3 bg-black/50 rounded-lg border border-white/5">
                    <div className="flex items-center gap-2">
                      <CheckCircle className="h-4 w-4 text-green-400" />
                      <span className="text-white text-sm">{product.name}</span>
                    </div>
                    <span className="text-white/40 text-xs">{product.discord_webhooks?.length || 0} webhook(s)</span>
                  </div>
                ))}
              </div>
            )}
            <Link 
              to="/panelgsnadminbackend/products" 
              className="flex items-center gap-2 text-amber-500 text-sm hover:text-amber-400 mt-3"
            >
              <ExternalLink className="h-4 w-4" />
              Manage Product Webhooks
            </Link>
          </div>
        </div>
      </div>
    </AdminLayout>
  );
}
