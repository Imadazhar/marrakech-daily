export type Category =
  | 'breaking-news'
  | 'business'
  | 'tourism'
  | 'real-estate'
  | 'culture'
  | 'events'
  | 'lifestyle'
  | 'opinion';

export interface Author {
  id: string;
  name: string;
  bio: string;
  avatar_url: string;
  title: string;
}

export interface Article {
  id: string;
  slug: string;
  title: string;
  excerpt: string;
  content: string;
  category: Category;
  author: Author;
  featured_image: string;
  featured_image_alt: string;
  published_at: string;
  reading_time: number;
  is_breaking: boolean;
  is_featured: boolean;
  tags: string[];
  seo_title?: string;
  seo_description?: string;
  view_count: number;
}
