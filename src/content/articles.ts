// FINAL COPY — do not edit wording, spelling or punctuation.
// Each article is stored as blocks so the layout can style headings,
// paragraphs and bullet points without touching the text itself.

export type Block =
  | { type: 'p'; text: string }
  | { type: 'h'; text: string }
  | { type: 'ul'; items: string[] }

export interface Article {
  id: SliceId
  crust: string
  title: string
  subtitle?: string
  blocks: Block[]
}

export type SliceId = 'seamone' | 'angels' | 'serena' | 'tomcat' | 'freeda' | 'stationf'

export const articles: Article[] = [
  {
    id: 'seamone',
    crust: 'Seamone Paris',
    title: 'Seamone Paris (read: See Money, Paris?)',
    blocks: [
      {
        type: 'p',
        text: 'Chiara Albano was, and is, an ESSEC student that started her own company and was celebrated for it in class. She called it Seamone Paris and they (likely only her) made ‘vintage’ dresses that came with a matching bandana, or was it called a hairband? Women’s fashion isn’t really my thing, spare me -Men’s fashion on the other hand?',
      },
      {
        type: 'p',
        text: 'She spent around €8000 to €10000 for her first ‘collection’, a catalogue of about 11-13 dresses made from fabrics she admittedly sourced near Montmartre.',
      },
      { type: 'p', text: 'Here’s some notes I took during the session:' },
      {
        type: 'p',
        text: "She initially went to a workshop with a minimum inventory that was too high. The production cost per dress is €40 and she sells the dress and the headband for €120. She does pop-ups and everything. She's sold around 400 total - she's got 200 in her house. She might have just broken even. Obviously, the €40 doesn't include her salary, only the production costs from the workshop in Toulouse. She orders the dresses at home. She gifts influencers products and gets about 10 sales per gift. She asked her friends to stand in queue for her pop ups to showcase social proof. Bootstrapping: She left her apartment and moved back in with her parents. Her models in her pictures are her friends and she doesn't have to pay them. Holy hell these guys are really breaking her down - she never refuses to answer anything and is exposing a little more than I think she should. The professor says that Chiara could be invited to Le Beaumarchais (owned by LVMH) that contains new brands.",
      },
      {
        type: 'p',
        text: 'What was interesting was one of my friends called her out on her €120 price point, and he mentioned that, very clearly, for him, that price was that of a luxury product. It’s fascinating how subjective luxury can be. She said that her product was priced with competitor prices in mind. Well, from what I heard from a little birdie from the cohort, it’s a rather gauche price for her, for she’s incredibly ‘loaded’ and this project might just be more ‘love money’ financed than self-financed.',
      },
    ],
  },
  {
    id: 'angels',
    crust: 'Business Angels',
    title: 'Angel Investors',
    subtitle: '(read: Borderline Racist Granddad’s Association of Know-it-alls)',
    blocks: [
      {
        type: 'p',
        text: 'Besides getting incorrectly racially profiled as a North African (which I’m not), while sitting next to a correctly racially profiled South Indian, and a few correctly racially profiled Chinese folks, I learnt quite a few things about the world of business angels. These guys were a part of the ESSEC Business Angels.',
      },
      { type: 'p', text: 'Here’s some notes I took during the session:' },
      {
        type: 'ul',
        items: [
          'Benjamin Bach made a joke about Eggs and Bacon in the morning - the chicken is involved, but the pig is committed. ESSEC Business angels are committed, apparently, to invest €20k a year per member. They have 35 members and have regular cocktails. He said it isn’t just granddads who are done with their careers, but people that want to be involved. He said that there’s a lot of passive ways to make money like the stock market. They look like ol’ guys that want to talk about hookers and blow in the ‘80s. They charge €100 and €600 for the Paris Business Angels as annual fees.',
          'BAs usually get in where there’s a bit of recurring revenue of around €200k and there’s a good few clients locked in a few contracts (for SaaS). These guys aren’t lenders, they’re equity investors. He talks about being sidecars of VC funding. VCs are impatient and request a certain IRR.',
          'They talk about how it’s very bad to raise money, because it’s a loan and or an equity share. As long as you can bootstrap, you are good to go - there’s no point in raising money unless you absolutely need to. They mentioned a company with a €20M turnover with a €2M EBIT.',
          'Europe isn’t good for €100M+ type of tickets, and usually companies have to go to the US for this. A lot off VCs a few years ago used to give away €20-€35M to spend on a bigger team and marketing and communication. Then there was a bit of a crash in terms of financing, and these companies that had basically wasted this money away didn’t get another round. Having a woman in your founders group is helpful because then it qualifies as DEI, since the world of entrepreneurship is still very male-dominated.',
          'Investors usually mostly invest in tech businesses, rather than brick-and-mortar businesses that are traditional. That’s the bias in the field of entrepreneurship that I’ve been thinking of. Another one of their criteria is that they look for entrepreneurs that are looking to have mentors and don’t just want money.',
        ],
      },
    ],
  },
  {
    id: 'serena',
    crust: 'Serena VC',
    title: 'Serena VC',
    blocks: [
      {
        type: 'p',
        text: 'The speaker, David Bitton is one of the most revered entrepreneurs in France. He was one of the first people to provide Internet access via cellular service, and he also had a competitor application to DoctoLib (which ended up getting a lot of funding, essentially pricing out Bitton’s company).',
      },
      {
        type: 'p',
        text: "He was about 60, with energy in his arms and salt and pepper in his hair. He said that they usually invest in two halves - they take half the funding upfront, and invest into a portfolio of start-ups, and they take the other half five years later (assuming there's a 10 year total lock-in), and then they optimize between the start-ups. They assume that two of the companies that are gonna invest in are gonna be unicorns, nothing more, nothing less. They've already got a lot of unicorns in their portfolio. Another cool concept he introduced us to was the concept of “vintages”. Probably, and most likely, a reference to the way individuals talk about old alcohol (1979 vintage Dom Perignon, etc.). He said that the only vintage that hasn't made profits is the 2008 vintage. By saying “vintage” for a certain year, they’re referring to the entire batch of investments they made in that particular year.",
      },
      {
        type: 'p',
        text: "He said that when you do approach a VC, make sure that their their investment cycle, which would be at the beginning of the first five-year rollout. He said the VCs would be keen on giving you a meeting because they want to see what young energetic entrepreneurs are doing and are up to, and maybe even pry on their ideas, but they really won't invest unless they're actually able to.",
      },
    ],
  },
  {
    id: 'tomcat',
    crust: 'TOMCAT',
    title: 'TOMCAT',
    blocks: [
      {
        type: 'p',
        text: 'TOMCAT is a VC that seems to care a lot about what happens after somebody has built the product. One of the big themes from their sessions was that founders spend an insane amount of time thinking about the product, the website and customer acquisition, and then almost treat pricing like something they can figure out in an afternoon. TOMCAT’s view is that pricing is a real function of the company, just like sales or marketing.',
      },
      {
        type: 'p',
        text: 'They’ve spent thousands of hours working (the speaker spent 10000+ hours) with founding teams, and some of their examples are pretty dramatic: changing the pricing structure or the way the product was packaged increased average contract value by 2x, 3x and even 6x in some cases. Sometimes the answer was not even something complicated. One company simply increased its prices and apparently saw no impact on conversion. The point is that founders often leave money on the table because they are scared of charging what the product is actually worth.',
      },
      {
        type: 'p',
        text: 'Their pricing framework is also useful because it forces you to admit that you cannot optimize everything at the same time. If your priority is acquisition, you probably want a lower price, low commitment and quite a lot of value upfront. If your priority is retention, you want customers to commit and gradually get more value. If your priority is monetization, you might deliberately limit what is available in the basic product so customers have a reason to upgrade. TOMCAT’s point is that the correct answer changes as the company changes. They reduce pricing to three fairly practical questions: what are you charging for, how have you packaged the features, and what is the actual price level? Even adding Starter, Pro and Advanced tiers can capture customers with very different willingness to pay instead of forcing everybody into the same €199 product.',
      },
    ],
  },
  {
    id: 'freeda',
    crust: 'Freeda',
    title: 'Free-Dough? (read: FREEDA)',
    blocks: [
      { type: 'h', text: 'General thoughts on their office and funding situation' },
      {
        type: 'p',
        text: 'The vibe of Freeda’s offices was very new-money, with a clearly freshly moved-into office just about three stones’ throws away from Les Halles. There were signs aplenty of deep pockets that were recently sewn, with a MacBook box on every desk, Bluetooth keyboards that make a lot of noise (maybe too much), but are fun to use, and two De’Longhi coffee machines that ate whole beans and spit out coffee - not one of those cheap Nespresso machines, or worse yet, those wretched vending machines - they don’t wish to be reminded of an RER station, now, do they?',
      },
      {
        type: 'p',
        text: 'How’d I know it was new money, you ask, if MacBooks and keyboards are commonplace in 2026? Because the MacBooks were all M5s that just came out, the keyboards were all mechanical, and the coffee machine was, well, a full-fledged coffee machine. Hell, even their desks were fancy - with some of them being height-adjustable in order for them to be converted to a standing-desk setup. They had a couple of xbox controllers laying around out back, indicating that the company doesn’t shy away from leisurely activities should they wish to blow off some steam (pun intended on steam, which happens to be a gaming service).',
      },
      {
        type: 'p',
        text: 'There are signs of monetary success and then there are billboards. I heard through the grapevine that Freeda has recently raised (read: given) a funding of €20 million for ‘business purposes’, and cousin, business is a-boomin’!',
      },
      { type: 'h', text: 'The presentations at FREEDA' },
      {
        type: 'p',
        text: 'A total of 8 groups presented their decks comparing two prospective clients for FREEDA, with the ultimate objective of recommending one over the other, coupled with a thorough pursuit plan with a list of possible contacts. We ended up putting together a deck full of a lot of things, not the least of which was a few screenshots of some people from ESSEC that worked at ICADE (our target company). Towards the end, the chief of staff came out to say a few words and give out ‘shout-outs’ or honorable mentions to some groups. He started with one, and then the other, and then another, and mine was nowhere to be found. I’d already accepted the possibility of a loss by this point. Just as I’d almost given up, he said “…but I think we can all agree that the ICADE group was the best!”, and the class burst out in claps. We were promised a reach out and some gift vouchers from FREEDA (from their €20 Mil?). It was truly a pleasure to win.',
      },
      { type: 'h', text: 'Thoughts on FREEDA’s self-awareness' },
      {
        type: 'p',
        text: 'Now, FREEDA is almost niche - they only function within the construction industry and provide due diligence services to upcoming projects (with the assistance of their own AI). Although they’ve identified a very niche sector of the market to function in, they’re also very self-aware about their domain and what they have to offer. They know that what they bring to the table may be done by AI come next month, and if this were a very fresh new startup, they probably would have a tough time raising funds because of AGI and how good AI’s gotten, and continues to get.',
      },
    ],
  },
  {
    id: 'stationf',
    crust: 'Station F',
    title: 'Prochain arrêt, Station F',
    blocks: [
      { type: 'h', text: 'The Vibe at Station F' },
      {
        type: 'p',
        text: 'Station F is essentially a large warehouse full of starry-eyed (or dollar-eyed?) kids trying to get their projects off the ground. It’s a place where you come see others doing well and take a little inspiration, make connections and alliances, and meet people like yourself (and maybe the best part is the friends you’ll make along the way!).',
      },
      { type: 'h', text: 'Gluten’s freed (Sally Lora)' },
      {
        type: 'p',
        text: 'Sally’s got two kids, and one of them was diagnosed with an autoimmune condition that prevents him from consuming gluten. She’s a good example of the “solve-your-own-problem” approach. She felt like there weren’t enough gluten-free options available for people in France. Therefore, she has a B2C product: her offer is to help food brands and food retailers make their gluten-free range better. Her product vision is a lot more clear for what she wants to build. She applied to Station F because she’s currently a solo founder, and she wants to be surrounded by other people that are building startups.',
      },
      { type: 'h', text: 'ESSEC Student Incubator' },
      {
        type: 'p',
        text: 'There are three phases - exploration, incubation and acceleration. They started a new thing this September called the startup cyber program. This gives ESSEC students the know-how in terms of cybersecurity and related concepts. They do startup days and events where people can find cofounders (mix and match - if you want a technical cofounder, etc., and they also invite other schools like École 42. They also make one where people can find an internship with a startup! There’s a startup pop up, and a very good vibe .',
      },
      {
        type: 'p',
        text: 'Deeptech refers to companies and technologies rooted in scientific discoveries, research, or advanced engineering rather than minor tweaks to existing software apps. It’s a rather recent phenomenon, and people coming from research don’t usually have good business or startup skills, and it’s a good opportunity to connect to talent across the pool. They recommend having two founders - one with a scientific mind, and one with a business mind. The minimum viable product for something like this would cost greatly. ESSEC champions Climate, Sustainability and Health deeptech. ESSEC’s DeepTech studio offers connecting scientific-leaning guys with business guys.',
      },
      { type: 'h', text: 'Groover (Romain)' },
      {
        type: 'p',
        text: "Romain has a music promotion startup that helps artists contact playlists and promote them. He started his entrepreneurial journey right after Berkeley in 2018. They’ve since raised €5M in equity and €5M in non-dilutive funding. There’s 3 of them, and all of them had a music background. Their chief competitor is a platform called SubmitHub. Their business model functions on the premise that you can't pay for exposure in the music industry. Therefore, they've gotten around that loophole by creating credits on their platform that you can buy, and then you can spend those credits on possible consideration for playlists. However, the key catch and the main point of conflict of interest, is that the curators of those playlists do not necessarily have to position your song on the playlist. That means technically somebody could just give you some copy paste type of feedback and get away with not putting any songs on their playlists whatsoever. That's what makes it a little bit of a tricky business. Reddit is full of reviews of people that are dissatisfied with this particular conflict of interest situation.",
      },
    ],
  },
]

export const articleById = Object.fromEntries(articles.map((a) => [a.id, a])) as Record<SliceId, Article>
