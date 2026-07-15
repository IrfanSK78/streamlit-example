"""Email templates and master voice for Invasive Outreach Agent."""

MASTER_TEMPLATE = """Hi [PERSON_NAME],

My name is Sonia Baig, and I'm with Invasive Design, a USA-based design and digital experience company.

I recently came across [COMPANY_NAME]'s opening for a [JOB_TITLE] in [LOCATION] and wanted to reach out because I believe there may be a strong alignment between the design challenges your team is addressing and the way we work at Invasive Design.

[PERSONALIZED_PARAGRAPH_1]

At Invasive Design, we combine experienced human designers with AI-assisted processes to accelerate research, exploration, analysis, prototyping, and production without compromising strategic or creative thinking.

Our work is psychology-driven. We look beyond how a digital product looks and focus on how users process information, respond to visual patterns, build habits, navigate complex journeys, and make decisions within an experience.

Our services include:

UX Research & Strategy
Information Architecture & Sitemap Planning
Wireframing & User Experience Design
UI Design & Design Systems
Responsive Website Design and Development
Social Media Marketing

Our team has had the opportunity to work with brands including Nike, Walmart.ca, PepsiCo, Canon, Nissan, and Bell, bringing experience across consumer brands, retail, digital products, and customer-focused experiences.

[PERSONALIZED_PARAGRAPH_2]

[PERSONALIZED_PARAGRAPH_3]

I would love to set up a quick call to introduce Invasive Design and explore whether we could support [COMPANY_NAME] as an external UX and product design partner.

You can schedule a time here:

https://calendar.app.google/syCR3jcssgrGjgde8

Our calendar currently reflects EST availability. However, we are happy to work around your local time and schedule a call at a time that is convenient for you.

Website:
https://invasived.com

LinkedIn:
https://www.linkedin.com/in/irfanshaikh78

Instagram:
https://www.instagram.com/invasived.studio

I look forward to connecting with you.

Best regards,

Sonia Baig
Principal Business Director
Invasive Design
+1 (757) 276-6153"""

FORBIDDEN_PHRASES = [
    "I hope this email finds you well",
    "game-changing",
    "revolutionary",
    "synergy",
    "was impressed by your innovative",
    "em dash",
    "em-dash",
    "emoji",
    "😊", "😃", "🚀", "💡", "✨"
]

PARAGRAPH_1_TEMPLATES = {
    'research_focus': "What particularly caught my attention was your team's focus on understanding user behavior and research-driven decision making. The role description suggests you're building experiences informed by genuine user insight, not assumptions.",
    'design_systems': "What particularly caught my attention was the emphasis on building scalable design systems and consistent experiences across your products. Creating systems that grow with your platform requires both strategic thinking and meticulous execution.",
    'multiple_disciplines': "What particularly caught my attention was the breadth of responsibilities the role encompasses—from research and strategy through design and implementation. This suggests your team is handling complex design challenges that benefit from diverse expertise.",
    'product_complexity': "What particularly caught my attention was the description of your product environment and the complexity of user journeys. The need to balance multiple stakeholder perspectives with user-centered design is something we work with regularly.",
    'transformation': "What particularly caught my attention was your focus on digital transformation and improving how users interact with your platform. This kind of strategic work requires both deep UX thinking and production discipline.",
    'experience_design': "What particularly caught my attention was your emphasis on creating cohesive customer experiences across multiple touchpoints. Building unified experiences across channels requires both strategic planning and detailed execution.",
}

PARAGRAPH_2_TEMPLATES = {
    'underresourced': "Instead of expecting one full-time designer to independently handle research, strategy, information architecture, wireframing, UI design, and design system evolution, you could explore access to a multidisciplinary design team that brings specialized expertise to each area.",
    'system_and_production': "Instead of asking one hire to manage both design system evolution and ongoing product work, you could access a team that can develop robust systems while maintaining production velocity.",
    'strategy_and_execution': "Instead of having one person balance strategic design thinking with implementation execution, you could partner with a team that separates these concerns and brings specialized expertise to each.",
    'research_and_design': "Instead of one designer managing both research activities and design execution, you could access a team where these disciplines are distinct and reinforcing.",
    'growth_and_operations': "As you scale your product, the gap between strategic design work and day-to-day production expands. A partnership approach allows you to maintain both without overloading a single hire.",
}

PARAGRAPH_3_TEMPLATES = {
    'b2b': "Your platform's complexity and the range of user personas suggests this is work where depth matters. We've worked with companies building similar B2B and SaaS experiences, and there's real value in having design partners who understand both the technical and human dimensions.",
    'consumer': "Your focus on consumer engagement and conversion metrics indicates this is work where user psychology and behavioral design are central. We've built experience across consumer brands and digital platforms where these insights drive real business impact.",
    'mobile': "The emphasis on mobile and responsive experience suggests you're serving users across contexts and devices. We bring experience designing for complex mobile-first environments where consistency and usability are competitive advantages.",
    'international': "Your international market presence means your design systems need to support multiple languages, cultural contexts, and regulatory environments. This level of complexity benefits from design partners who have navigated similar challenges.",
    'market_position': "The competitive pressures in your market mean that user experience is a differentiator. We focus on the strategic and psychological dimensions that create lasting competitive advantage through design.",
}

def build_personalized_paragraph(template_dict, themes, job_description, company_name):
    """
    Build a personalized paragraph from themes and job description.
    Returns: personalized text
    """
    highest_match = None
    highest_score = 0

    for template_key, template_text in template_dict.items():
        score = 0
        for theme in themes:
            if theme.lower() in template_text.lower():
                score += 1

        if score > highest_score:
            highest_score = score
            highest_match = template_text

    if highest_match:
        return highest_match

    return list(template_dict.values())[0]

def validate_email(email_text):
    """
    Check email for forbidden phrases or patterns.
    Returns: (is_valid, warnings)
    """
    warnings = []
    email_lower = email_text.lower()

    for phrase in FORBIDDEN_PHRASES:
        if phrase.lower() in email_lower:
            warnings.append(f"Contains forbidden phrase: '{phrase}'")

    if email_text.count('\n') > 50:
        warnings.append("Email is very long (50+ line breaks)")

    if email_text.count('[') > 5:
        warnings.append("Email contains many unfilled placeholders")

    return len(warnings) == 0, warnings
