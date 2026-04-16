import { Helmet } from 'react-helmet-async';

const SITE_URL = 'https://gameshopnepal.com';
const SITE_NAME = 'GameShop Nepal';
const DEFAULT_IMAGE = 'https://customer-assets.emergentagent.com/job_f826d6c3-4354-45f7-8eac-b606d3ae45c3/artifacts/8kg7y2go_Staff.jpg';

/**
 * SEO Component — Uses react-helmet-async to inject meta tags into <head>
 * Crawlers see these tags even before JS finishes executing
 */
export default function SEO({ 
  title = 'GameShop Nepal | Netflix, Spotify, YouTube Premium & Prime Video at Best Prices',
  description = 'Buy Netflix, Spotify Premium, YouTube Premium, Amazon Prime Video subscriptions at best prices in Nepal. Instant delivery guaranteed!',
  keywords = 'Netflix Nepal, Spotify Premium Nepal, YouTube Premium Nepal, Prime Video Nepal, streaming services Nepal, digital subscription Nepal',
  image = DEFAULT_IMAGE,
  url,
  type = 'website',
  schema = null
}) {
  const fullUrl = url || (typeof window !== 'undefined' ? window.location.href.replace(/https?:\/\/[^/]+/, SITE_URL) : SITE_URL);

  return (
    <Helmet>
      <title>{title}</title>
      <meta name="description" content={description} />
      <meta name="keywords" content={keywords} />
      <link rel="canonical" href={fullUrl} />

      {/* Open Graph */}
      <meta property="og:type" content={type} />
      <meta property="og:url" content={fullUrl} />
      <meta property="og:title" content={title} />
      <meta property="og:description" content={description} />
      <meta property="og:image" content={image} />
      <meta property="og:site_name" content={SITE_NAME} />
      <meta property="og:locale" content="ne_NP" />
      <meta property="og:locale:alternate" content="en_US" />

      {/* Twitter */}
      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:title" content={title} />
      <meta name="twitter:description" content={description} />
      <meta name="twitter:image" content={image} />

      {/* JSON-LD Structured Data */}
      {schema && (
        <script type="application/ld+json">{JSON.stringify(schema)}</script>
      )}
    </Helmet>
  );
}

// Pre-built SEO configs for common pages
export const SEOConfigs = {
  home: {
    title: 'Netflix, Spotify Premium, YouTube Premium Nepal | GameShop Nepal',
    description: 'Buy Netflix, Spotify Premium, YouTube Premium, Amazon Prime Video, Disney+ Hotstar subscriptions at best prices in Nepal. Instant delivery guaranteed!',
    keywords: 'Netflix Nepal, Spotify Premium Nepal, YouTube Premium Nepal, Prime Video Nepal, Netflix subscription price Nepal, streaming services Nepal, OTT platforms Nepal, digital subscription Kathmandu',
  },
  about: {
    title: 'About Us - Trusted Digital Products Store | GameShop Nepal',
    description: 'GameShop Nepal — Nepal\'s most trusted digital products store. Buy Netflix, Spotify, YouTube Premium with instant delivery. 100% genuine products.',
    keywords: 'GameShop Nepal about, trusted digital store Nepal, Netflix seller Nepal, Spotify dealer Nepal',
  },
  faq: {
    title: 'FAQ - How to Buy Netflix, Spotify in Nepal? | GameShop Nepal',
    description: 'How to buy Netflix, Spotify Premium, YouTube Premium in Nepal? Payment methods, delivery time, all answers here.',
    keywords: 'how to buy Netflix Nepal, Spotify Premium Nepal FAQ, YouTube Premium Nepal FAQ, streaming subscription guide Nepal',
    schema: {
      '@context': 'https://schema.org',
      '@type': 'FAQPage',
      mainEntity: []
    }
  },
  blog: {
    title: 'Netflix, Spotify, YouTube Tips & Guides | GameShop Nepal Blog',
    description: 'Netflix guides, Spotify Premium features, YouTube Premium benefits. Streaming guides, gaming tips, and digital product tutorials.',
    keywords: 'Netflix guide Nepal, Spotify tips, YouTube Premium features, streaming guide Nepal',
  },
  reviews: {
    title: 'Customer Reviews - Trusted by Thousands | GameShop Nepal',
    description: 'Read real customer reviews of GameShop Nepal. Rated 4.7/5 on Trustpilot. See why thousands trust us for Netflix, Spotify, YouTube Premium subscriptions.',
    keywords: 'GameShop Nepal reviews, GameShop Nepal trustpilot, Netflix Nepal reviews, digital subscription reviews Nepal',
  },
  terms: {
    title: 'Terms of Service | GameShop Nepal',
    description: 'Terms and conditions for using GameShop Nepal services.',
    keywords: 'GameShop Nepal terms, service terms Nepal',
  },
  track: {
    title: 'Track Your Order | GameShop Nepal',
    description: 'Track your Netflix, Spotify, YouTube Premium order status in real-time.',
    keywords: 'track order Nepal, order status Nepal, delivery tracking Nepal',
  },
  reseller: {
    title: 'Reseller Plans - Earn Money Selling Digital Products | GameShop Nepal',
    description: 'Become a GameShop Nepal reseller. Earn commissions selling Netflix, Spotify, YouTube Premium subscriptions. Multiple tier plans available.',
    keywords: 'GameShop Nepal reseller, digital products reseller Nepal, Netflix reseller Nepal, earn money Nepal',
  },
};

// Product SEO helper
export function getProductSEO(product) {
  if (!product) return SEOConfigs.home;
  
  const minPrice = product.variations?.length 
    ? Math.min(...product.variations.map(v => v.price))
    : 0;
  
  const cleanDescription = product.description
    ?.replace(/<[^>]*>/g, '')
    ?.slice(0, 160) || '';

  return {
    title: `Buy ${product.name} in Nepal - Rs ${minPrice} | GameShop Nepal`,
    description: `${product.name} at best price in Nepal. Starting Rs ${minPrice}. Instant delivery. ${cleanDescription}`,
    keywords: `${product.name} Nepal, ${product.name} price Nepal, buy ${product.name} Nepal, ${product.name} subscription Nepal`,
    image: product.image_url,
    type: 'product',
    schema: {
      '@context': 'https://schema.org',
      '@type': 'Product',
      name: product.name,
      description: cleanDescription || `Buy ${product.name} at best price in Nepal`,
      image: product.image_url,
      url: `${SITE_URL}/product/${product.slug}`,
      brand: {
        '@type': 'Brand',
        name: product.name.split(' ')[0]
      },
      offers: {
        '@type': 'AggregateOffer',
        lowPrice: minPrice,
        priceCurrency: 'NPR',
        availability: product.is_sold_out 
          ? 'https://schema.org/OutOfStock'
          : 'https://schema.org/InStock',
        seller: {
          '@type': 'Organization',
          name: 'GameShop Nepal',
          url: SITE_URL
        },
        priceValidUntil: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
      }
    },
  };
}

// Blog post SEO helper
export function getBlogSEO(post) {
  if (!post) return SEOConfigs.blog;
  return {
    title: `${post.title} | GameShop Nepal Blog`,
    description: post.excerpt || post.content?.replace(/<[^>]*>/g, '').slice(0, 160),
    image: post.image_url,
    type: 'article',
    schema: {
      '@context': 'https://schema.org',
      '@type': 'BlogPosting',
      headline: post.title,
      description: post.excerpt,
      image: post.image_url,
      datePublished: post.created_at,
      author: { '@type': 'Organization', name: 'GameShop Nepal' },
      publisher: { '@type': 'Organization', name: 'GameShop Nepal', url: SITE_URL },
    },
  };
}

export { SITE_URL, SITE_NAME, DEFAULT_IMAGE };
