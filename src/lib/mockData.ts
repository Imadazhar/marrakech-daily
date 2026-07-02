import { Article, Author, Event } from '../types';

export const authors: Author[] = [
  {
    id: '1',
    name: 'Sarah Mitchell',
    bio: 'Senior correspondent covering Marrakech business and investment. Former Bloomberg journalist based in the Red City since 2019.',
    avatar_url: 'https://i.pravatar.cc/150?img=47',
    title: 'Senior Correspondent',
  },
  {
    id: '2',
    name: 'Karim Benali',
    bio: 'Culture and tourism editor. Born in Marrakech, covering the city\'s transformation for international audiences.',
    avatar_url: 'https://i.pravatar.cc/150?img=12',
    title: 'Culture & Tourism Editor',
  },
  {
    id: '3',
    name: 'Jessica Hart',
    bio: 'Real estate and lifestyle reporter. Digital nomad turned Marrakech expat, now your guide to living in the Ochre City.',
    avatar_url: 'https://i.pravatar.cc/150?img=49',
    title: 'Real Estate & Lifestyle Reporter',
  },
];

export const mockArticles: Article[] = [
  {
    id: '1',
    slug: 'marrakech-airport-new-terminal-2025',
    title: 'Marrakech Menara Airport Breaks Ground on $400M Terminal Expansion',
    excerpt: 'The new terminal will increase annual capacity to 12 million passengers, positioning Marrakech as North Africa\'s premier aviation hub.',
    content: `# Marrakech Menara Airport Breaks Ground on $400M Terminal Expansion

MARRAKECH — Officials from Morocco's National Airports Office (ONDA) joined regional and national government leaders Thursday to break ground on a major expansion of Menara Airport that will transform the facility into one of North Africa's busiest aviation hubs.

The €370 million ($400 million) project will add a dedicated international terminal spanning 85,000 square meters, doubling the airport's current passenger processing capacity to approximately 12 million travelers annually.

"This investment reflects our confidence in Marrakech as a world-class destination," said the Regional Governor during the ceremony, held on the airport's western tarmac. "We are building infrastructure for the next generation of visitors and investors."

## What's Being Built

The expansion includes a new international arrivals hall featuring traditional Moroccan architectural motifs, an expanded duty-free commercial zone with 40 new retail units, premium passenger lounges, and upgraded baggage handling systems capable of processing 6,000 bags per hour.

The project also incorporates a new direct rail link to the city center — a 14-minute connection to Gueliz station — eliminating the need for taxi or bus transfers for many travelers.

Construction will proceed in two phases, with Phase 1 expected for completion before the 2030 FIFA World Cup, which Morocco will co-host.

## Tourism Context

Marrakech welcomed 4.2 million international visitors in 2024, a record figure representing 23% growth over the previous year. Demand for direct flights from European capitals has consistently outpaced available capacity, with routes from London, Paris, Madrid, and Amsterdam frequently sold out months in advance.

Industry analysts estimate the expansion could attract 8 to 12 new direct routes from North American cities, including New York JFK, Toronto Pearson, and Miami International.

"The airport has been the binding constraint on Marrakech's tourism potential," said Ahmed Fassi, director of the Marrakech Tourism Council. "This investment removes that ceiling."

## Economic Impact

The government projects the project will generate 4,500 construction jobs and 800 permanent operational positions. Local contractors have been prioritized, with 70% of subcontracting reserved for Marrakech-based firms.

Real estate analysts are already noting increased interest in hotel and resort development near the airport corridor, particularly along the Route de l'Ourika, where several parcels are under negotiation by international hospitality groups.`,
    category: 'breaking-news',
    author: authors[0],
    featured_image: 'https://images.unsplash.com/photo-1436491865332-7a61a109cc05?w=1200&q=80',
    featured_image_alt: 'Airplane taking off at sunset over Marrakech airport',
    published_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    reading_time: 4,
    is_breaking: true,
    is_featured: true,
    tags: ['airport', 'infrastructure', 'tourism', 'investment', 'transport'],
    seo_title: 'Marrakech Airport $400M Expansion: New Terminal, Rail Link & 12M Capacity',
    seo_description: 'Marrakech Menara Airport breaks ground on transformative $400M expansion adding a new international terminal and city rail link ahead of 2030 World Cup.',
    view_count: 8420,
  },
  {
    id: '2',
    slug: 'luxury-riad-boom-medina-2025',
    title: '14 Luxury Riads Open in Medina as High-End Tourism Demand Surges',
    excerpt: 'International investors are pouring capital into Marrakech\'s ancient medina, converting historic palaces into ultra-luxury boutique hotels fetching $2,000 per night.',
    content: 'Full article content here...',
    category: 'tourism',
    author: authors[1],
    featured_image: 'https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=1200&q=80',
    featured_image_alt: 'Ornate Moroccan riad courtyard with traditional tilework and fountain',
    published_at: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
    reading_time: 3,
    is_breaking: false,
    is_featured: true,
    tags: ['luxury', 'riad', 'medina', 'tourism', 'hospitality'],
    view_count: 6231,
  },
  {
    id: '3',
    slug: 'gueliz-tech-startup-hub-silicon-medina',
    title: '"Silicon Medina": How Gueliz Is Becoming Morocco\'s Hottest Tech Hub',
    excerpt: 'With co-working spaces, VC funding, and digital nomads arriving daily, Marrakech\'s new town is quietly building a startup ecosystem that rivals Casablanca.',
    content: 'Full article content here...',
    category: 'business',
    author: authors[0],
    featured_image: 'https://images.unsplash.com/photo-1497366216548-37526070297c?w=1200&q=80',
    featured_image_alt: 'Modern co-working space in Gueliz Marrakech with laptop workers',
    published_at: new Date(Date.now() - 8 * 60 * 60 * 1000).toISOString(),
    reading_time: 5,
    is_breaking: false,
    is_featured: false,
    tags: ['startup', 'tech', 'gueliz', 'business', 'investment'],
    view_count: 4890,
  },
  {
    id: '4',
    slug: 'palmeraie-real-estate-prices-surge',
    title: 'Palmeraie Property Prices Jump 28% as Foreign Buyers Flood Market',
    excerpt: 'French, British, and American buyers are driving record demand for villas in Marrakech\'s iconic palm grove, pushing prime prices above €4,000 per square meter.',
    content: 'Full article content here...',
    category: 'real-estate',
    author: authors[2],
    featured_image: 'https://images.unsplash.com/photo-1613490493576-7fde63acd811?w=1200&q=80',
    featured_image_alt: 'Luxury villa with pool surrounded by palm trees in Marrakech Palmeraie',
    published_at: new Date(Date.now() - 12 * 60 * 60 * 1000).toISOString(),
    reading_time: 4,
    is_breaking: false,
    is_featured: false,
    tags: ['real-estate', 'palmeraie', 'property', 'investment', 'villas'],
    view_count: 5670,
  },
  {
    id: '5',
    slug: 'jemaa-el-fna-gnawa-music-festival',
    title: 'Gnawa Music Festival Returns to Jemaa el-Fna with Record 40 International Acts',
    excerpt: 'The beloved annual festival celebrates its 25th anniversary with an expanded lineup blending traditional Moroccan Gnawa masters with jazz, soul, and electronic artists.',
    content: 'Full article content here...',
    category: 'culture',
    author: authors[1],
    featured_image: 'https://images.unsplash.com/photo-1539043474340-5e63e16b8a6c?w=1200&q=80',
    featured_image_alt: 'Gnawa musician performing at night with traditional instruments in Marrakech',
    published_at: new Date(Date.now() - 18 * 60 * 60 * 1000).toISOString(),
    reading_time: 3,
    is_breaking: false,
    is_featured: false,
    tags: ['gnawa', 'festival', 'music', 'culture', 'jemaa-el-fna'],
    view_count: 3910,
  },
  {
    id: '6',
    slug: 'best-new-restaurants-marrakech-2025',
    title: '10 Must-Try New Restaurants That Opened in Marrakech This Season',
    excerpt: 'From a rooftop Moroccan-Japanese fusion spot in Hivernage to a hidden courtyard trattoria in the medina, Marrakech\'s dining scene has never been more exciting.',
    content: 'Full article content here...',
    category: 'lifestyle',
    author: authors[2],
    featured_image: 'https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=1200&q=80',
    featured_image_alt: 'Elegant Moroccan restaurant interior with traditional lanterns and tile work',
    published_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
    reading_time: 6,
    is_breaking: false,
    is_featured: false,
    tags: ['restaurants', 'food', 'dining', 'lifestyle', 'guide'],
    view_count: 9820,
  },
  {
    id: '7',
    slug: 'marrakech-tram-extension-route-2025',
    title: 'City Council Approves Tram Extension Linking Medina to Semlalia District',
    excerpt: 'The 4.2km extension, approved unanimously, will reduce car traffic through the historic city center by an estimated 15% and launch by end of 2026.',
    content: 'Full article content here...',
    category: 'breaking-news',
    author: authors[0],
    featured_image: 'https://images.unsplash.com/photo-1551699026-d7f451591086?w=1200&q=80',
    featured_image_alt: 'Modern tram on city street in Morocco',
    published_at: new Date(Date.now() - 30 * 60 * 60 * 1000).toISOString(),
    reading_time: 3,
    is_breaking: true,
    is_featured: false,
    tags: ['transport', 'infrastructure', 'tram', 'city', 'development'],
    view_count: 7140,
  },
  {
    id: '8',
    slug: 'carre-eden-expansion-shopping',
    title: 'Carré Eden Mall Announces €45M Expansion with 80 New Retail Tenants',
    excerpt: 'Marrakech\'s premier luxury shopping destination will add a dedicated lifestyle wing featuring international brands not yet available elsewhere in Morocco.',
    content: 'Full article content here...',
    category: 'business',
    author: authors[0],
    featured_image: 'https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=1200&q=80',
    featured_image_alt: 'Modern shopping mall interior with luxury boutiques',
    published_at: new Date(Date.now() - 36 * 60 * 60 * 1000).toISOString(),
    reading_time: 3,
    is_breaking: false,
    is_featured: false,
    tags: ['retail', 'shopping', 'business', 'investment', 'gueliz'],
    view_count: 4320,
  },
];

export const mockEvents: Event[] = [
  {
    id: '1',
    title: 'Marrakech International Film Festival',
    description: 'The premier film festival in Africa showcasing world cinema, Moroccan productions, and international premieres.',
    location: 'Palais des Congrès, Hivernage',
    start_date: new Date(Date.now() + 3 * 24 * 60 * 60 * 1000).toISOString(),
    end_date: new Date(Date.now() + 10 * 24 * 60 * 60 * 1000).toISOString(),
    category: 'culture',
    price: 'Free – 250 MAD',
    organizer: 'Festival International du Film de Marrakech',
    external_url: 'https://www.festivalmarrakech.info',
  },
  {
    id: '2',
    title: 'Jemaa el-Fna Night Market',
    description: 'Experience the legendary nightly transformation of Jemaa el-Fna with food stalls, storytellers, and performers.',
    location: 'Jemaa el-Fna, Medina',
    start_date: new Date().toISOString(),
    end_date: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString(),
    category: 'lifestyle',
    price: 'Free entry',
    organizer: 'City of Marrakech',
  },
  {
    id: '3',
    title: 'Morocco Investment Forum 2025',
    description: 'Annual gathering of foreign investors, government officials, and business leaders focused on Morocco\'s economic opportunities.',
    location: 'Sofitel Marrakech Lounge & Spa',
    start_date: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
    end_date: new Date(Date.now() + 8 * 24 * 60 * 60 * 1000).toISOString(),
    category: 'business',
    price: '3,500 MAD',
    organizer: 'AMDIE',
  },
  {
    id: '4',
    title: 'Atlas Mountains Day Trek — Guided',
    description: 'Professional guided trekking to the Toubkal National Park foothills departing from Marrakech.',
    location: 'Departs Djemaa el-Fna',
    start_date: new Date(Date.now() + 2 * 24 * 60 * 60 * 1000).toISOString(),
    end_date: new Date(Date.now() + 2 * 24 * 60 * 60 * 1000).toISOString(),
    category: 'tourism',
    price: '450 MAD',
    organizer: 'Marrakech Adventure Tours',
  },
];
