import { useEffect } from 'react';

/**
 * SEO Component - Updates document head with meta tags
 * Usage: <SEO title="Page Title" description="..." image="..." />
 */
export default function SEO({ 
  title = 'GameShop Nepal | Netflix, Spotify, YouTube Premium & Prime Video सस्तोमा किन्नुहोस्',
  description = 'नेपालमा Netflix, Spotify Premium, YouTube Premium, Amazon Prime Video सबैभन्दा सस्तो दरमा किन्नुहोस्। तुरुन्त डेलिभरी, १००% असली प्रोडक्ट। Buy Netflix, Spotify, YouTube Premium in Nepal at best prices. Instant delivery guaranteed.',
  keywords = 'Netflix Nepal, Spotify Premium Nepal, YouTube Premium Nepal, Prime Video Nepal, Netflix subscription Nepal, Spotify कसरी किन्ने, YouTube Premium price Nepal, streaming services Nepal, digital subscription Nepal, Netflix सस्तोमा, OTT subscription Nepal',
  image = 'https://customer-assets.emergentagent.com/job_8ec93a6a-4f80-4dde-b760-4bc71482fa44/artifacts/4uqt5osn_Staff.zip%20-%201.png',
  url = typeof window !== 'undefined' ? window.location.href : '',
  type = 'website',
  schema = null
}) {
  useEffect(() => {
    // Update title
    document.title = title;

    // Update meta tags
    updateMetaTag('description', description);
    updateMetaTag('keywords', keywords);
    
    // Open Graph
    updateMetaTag('og:title', title, 'property');
    updateMetaTag('og:description', description, 'property');
    updateMetaTag('og:image', image, 'property');
    updateMetaTag('og:url', url, 'property');
    updateMetaTag('og:type', type, 'property');
    updateMetaTag('og:site_name', 'GameShop Nepal', 'property');
    
    // Twitter
    updateMetaTag('twitter:card', 'summary_large_image');
    updateMetaTag('twitter:title', title);
    updateMetaTag('twitter:description', description);
    updateMetaTag('twitter:image', image);

    // Schema.org JSON-LD
    if (schema) {
      let schemaScript = document.querySelector('script[data-schema="page"]');
      if (!schemaScript) {
        schemaScript = document.createElement('script');
        schemaScript.type = 'application/ld+json';
        schemaScript.setAttribute('data-schema', 'page');
        document.head.appendChild(schemaScript);
      }
      schemaScript.textContent = JSON.stringify(schema);
    }

    // Cleanup
    return () => {
      const schemaScript = document.querySelector('script[data-schema="page"]');
      if (schemaScript) {
        schemaScript.remove();
      }
    };
  }, [title, description, keywords, image, url, type, schema]);

  return null;
}

function updateMetaTag(name, content, attribute = 'name') {
  let tag = document.querySelector(`meta[${attribute}="${name}"]`);
  if (!tag) {
    tag = document.createElement('meta');
    tag.setAttribute(attribute, name);
    document.head.appendChild(tag);
  }
  tag.setAttribute('content', content);
}

// Pre-built SEO configs for common pages
export const SEOConfigs = {
  home: {
    title: 'Netflix, Spotify Premium, YouTube Premium Nepal मा सबैभन्दा सस्तो | GameShop Nepal',
    description: 'नेपालमा Netflix Subscription, Spotify Premium, YouTube Premium, Amazon Prime Video, Disney+ Hotstar सबैभन्दा सस्तो दरमा किन्नुहोस्। तुरुन्त डेलिभरी। Buy streaming subscriptions at best prices in Nepal with instant delivery!',
    keywords: 'Netflix Nepal, Spotify Premium Nepal, YouTube Premium Nepal, Prime Video Nepal, Netflix subscription price Nepal, Spotify कसरी किन्ने, YouTube Premium कति पर्छ, streaming services Nepal, OTT platforms Nepal, Netflix सस्तोमा, digital subscription Kathmandu',
  },
  about: {
    title: 'About Us - Nepal को Trusted Digital Products Store | GameShop Nepal',
    description: 'GameShop Nepal - नेपालमा सबैभन्दा भरपर्दो डिजिटल प्रोडक्ट स्टोर। Netflix, Spotify, YouTube Premium तुरुन्त डेलिभरी। १००% असली प्रोडक्ट। Your trusted source for streaming subscriptions since 2021.',
    keywords: 'GameShop Nepal about, trusted digital store Nepal, Netflix seller Nepal, Spotify dealer Nepal, streaming subscription Nepal',
  },
  faq: {
    title: 'FAQ - नेपालमा Netflix, Spotify कसरी किन्ने? | GameShop Nepal',
    description: 'Netflix, Spotify Premium, YouTube Premium नेपालमा कसरी किन्ने? पेमेन्ट कसरी गर्ने? तुरुन्त डेलिभरी कति समयमा? सबै जवाफ यहाँ। Find answers about ordering streaming subscriptions in Nepal.',
    keywords: 'how to buy Netflix Nepal, Spotify Premium कसरी किन्ने, YouTube Premium Nepal FAQ, streaming subscription guide Nepal, payment methods Nepal',
  },
  blog: {
    title: 'Netflix, Spotify, YouTube Tips & Guides नेपालीमा | GameShop Nepal Blog',
    description: 'Netflix कसरी प्रयोग गर्ने, Spotify Premium features, YouTube Premium benefits नेपालीमा। Streaming guides, gaming tips, and digital product tutorials.',
    keywords: 'Netflix guide Nepal, Spotify tips Nepali, YouTube Premium features, streaming guide Nepal, OTT tutorial Nepali',
  },
  terms: {
    title: 'Terms of Service - सेवाका शर्तहरू | GameShop Nepal',
    description: 'GameShop Nepal को सेवा प्रयोग गर्नका लागि नियम र शर्तहरू। Terms and conditions for using GameShop Nepal services.',
    keywords: 'GameShop Nepal terms, service terms Nepal, legal terms',
  },
  track: {
    title: 'Track Your Order - आफ्नो अर्डर ट्र्याक गर्नुहोस् | GameShop Nepal',
    description: 'तपाईंको Netflix, Spotify, YouTube Premium अर्डर कहाँ पुग्यो हेर्नुहोस्। Track your streaming subscription order status in real-time.',
    keywords: 'track order Nepal, order status Nepal, delivery tracking Nepal',
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

  // Nepali product name mappings for better SEO
  const nepaliNames = {
    'Netflix': 'नेटफ्लिक्स',
    'Spotify': 'स्पोटिफाई',
    'YouTube': 'युट्युब',
    'Prime': 'प्राइम',
    'Disney': 'डिज्नी'
  };
  
  let nepaliName = product.name;
  Object.entries(nepaliNames).forEach(([en, np]) => {
    if (product.name.toLowerCase().includes(en.toLowerCase())) {
      nepaliName = np;
    }
  });

  return {
    title: `${product.name} नेपालमा किन्नुहोस् Rs ${minPrice} मा | GameShop Nepal`,
    description: `${product.name} (${nepaliName}) नेपालमा सबैभन्दा सस्तो दरमा। Rs ${minPrice} देखि सुरु। तुरुन्त डेलिभरी। ${cleanDescription} Buy ${product.name} in Nepal at best price with instant delivery.`,
    keywords: `${product.name} Nepal, ${product.name} price Nepal, ${product.name} कति पर्छ, ${nepaliName} Nepal, buy ${product.name} Kathmandu, ${product.name} subscription Nepal, ${product.name} सस्तोमा`,
    image: product.image_url,
    type: 'product',
    schema: {
      '@context': 'https://schema.org',
      '@type': 'Product',
      name: `${product.name} - Nepal`,
      description: cleanDescription,
      image: product.image_url,
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
          url: 'https://git-sync-13.preview.emergentagent.com'
        },
        priceValidUntil: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
      },
      aggregateRating: {
        '@type': 'AggregateRating',
        ratingValue: '4.8',
        reviewCount: '150'
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
      author: {
        '@type': 'Organization',
        name: 'GameShop Nepal',
      },
    },
  };
}
