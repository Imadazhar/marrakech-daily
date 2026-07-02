import OpenAI from 'openai';

export const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY!,
});

export async function generateArticle(topic: string, category: string) {
  const completion = await openai.chat.completions.create({
    model: 'gpt-4o',
    messages: [
      {
        role: 'system',
        content: `You are a professional journalist for Marrakech Daily, an English-language local news website focused on Marrakech, Morocco. Write accurate, well-sourced, engaging articles. Always include specific details about Marrakech locations, neighborhoods, and context. Write in a style similar to USA Today but with local Marrakech flavor.`,
      },
      {
        role: 'user',
        content: `Write a complete news article about: ${topic}
Category: ${category}

Return a JSON object with:
- title: SEO-optimized headline (max 80 chars)
- excerpt: 2-sentence summary (max 160 chars)
- content: Full article in markdown (600-900 words)
- seo_title: Meta title
- seo_description: Meta description (max 155 chars)
- tags: Array of 5 relevant tags
- reading_time: Estimated minutes
- social_twitter: Tweet-length summary
- social_linkedin: LinkedIn post summary
- image_prompt: DALL-E prompt for featured image`,
      },
    ],
    response_format: { type: 'json_object' },
  });

  return JSON.parse(completion.choices[0].message.content!);
}

export async function generateDailyArticles() {
  const topics = [
    { topic: 'New luxury riad hotel opening in Marrakech medina', category: 'tourism' },
    { topic: 'Marrakech Menara Airport international flight expansion 2025', category: 'business' },
    { topic: 'Gueliz district new restaurant and café openings', category: 'lifestyle' },
    { topic: 'Real estate property market update Marrakech Palmeraie', category: 'real-estate' },
    { topic: 'Marrakech city council infrastructure development project', category: 'breaking-news' },
    { topic: 'Jemaa el-Fna square cultural festival announcement', category: 'culture' },
    { topic: 'Foreign investment startup scene Marrakech tech hub', category: 'business' },
    { topic: 'Weekend events guide Marrakech', category: 'events' },
    { topic: 'Expat guide living in Marrakech neighborhood tips', category: 'lifestyle' },
    { topic: 'Morocco tourism record visitors Marrakech 2025', category: 'tourism' },
  ];

  const articles = [];
  for (const t of topics) {
    const article = await generateArticle(t.topic, t.category);
    articles.push({ ...article, category: t.category });
  }
  return articles;
}
